"""Integración OpenAI: archivos, Responses API y code interpreter."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.db.models import AgentFileModel, AgentModel
from app.backend.utils.agent_document_index import strip_html
from app.backend.utils.agent_files import agent_dir

logger = logging.getLogger(__name__)

CONTAINER_TTL = timedelta(minutes=18)


class OpenAIUploadError(RuntimeError):
    """Fallo al subir un archivo a OpenAI."""


def _utcnow() -> datetime:
    return datetime.utcnow()


def is_container_expired(updated_at: datetime | None) -> bool:
    if not updated_at:
        return True
    return _utcnow() - updated_at > CONTAINER_TTL


def get_openai_client():
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY no configurada")
    from openai import OpenAI

    return OpenAI(api_key=settings.openai_api_key)


def upload_bytes_to_openai(content: bytes, display_name: str) -> str:
    from io import BytesIO

    client = get_openai_client()
    handle = BytesIO(content)
    uploaded = client.files.create(file=(display_name, handle), purpose="assistants")
    return uploaded.id


def require_openai_file_upload(content: bytes, display_name: str) -> str:
    if not settings.openai_api_key:
        raise OpenAIUploadError("OPENAI_API_KEY no configurada")
    try:
        leaf_name = display_name.replace("\\", "/").split("/")[-1] or display_name
        return upload_bytes_to_openai(content, leaf_name)
    except OpenAIUploadError:
        raise
    except Exception as exc:
        raise OpenAIUploadError(str(exc)) from exc


def upload_local_file_to_openai(file_path: Path, display_name: str | None = None) -> str:
    client = get_openai_client()
    upload_name = display_name or file_path.name
    with file_path.open("rb") as handle:
        uploaded = client.files.create(file=(upload_name, handle), purpose="assistants")
    return uploaded.id


def delete_openai_file(file_id: str | None) -> None:
    if not file_id or not settings.openai_api_key:
        return
    try:
        client = get_openai_client()
        client.files.delete(file_id)
    except Exception as exc:
        logger.warning("No se pudo eliminar archivo OpenAI %s: %s", file_id, exc)


def attach_file_to_container(container_id: str, file_id: str) -> None:
    client = get_openai_client()
    client.containers.files.create(container_id, file_id=file_id)


def clear_agent_container(agent: AgentModel) -> None:
    agent.openai_container_id = None
    agent.openai_container_updated_at = None


def ensure_openai_file_for_row(
    db: Session,
    agent: AgentModel,
    row: AgentFileModel,
    disk_path: Path,
) -> str | None:
    if row.openai_file_id:
        if agent.openai_container_id and not is_container_expired(agent.openai_container_updated_at):
            try:
                attach_file_to_container(agent.openai_container_id, row.openai_file_id)
            except Exception as exc:
                logger.warning("Contenedor expirado o inválido, se creará uno nuevo: %s", exc)
                clear_agent_container(agent)
        return row.openai_file_id

    if not settings.openai_api_key:
        raise OpenAIUploadError("OPENAI_API_KEY no configurada")

    try:
        file_id = upload_local_file_to_openai(disk_path, row.display_name)
        row.openai_file_id = file_id
        row.openai_upload_error = None
        db.flush()

        if agent.openai_container_id and not is_container_expired(agent.openai_container_updated_at):
            try:
                attach_file_to_container(agent.openai_container_id, file_id)
            except Exception as exc:
                logger.warning("No se pudo adjuntar archivo al contenedor existente: %s", exc)
                clear_agent_container(agent)
        return file_id
    except Exception as exc:
        row.openai_upload_error = str(exc)[:500]
        logger.exception("Error subiendo archivo a OpenAI: %s", row.id)
        return None


def sync_agent_openai_files(db: Session, agent_id: str) -> list[str]:
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        return []

    rows = (
        db.query(AgentFileModel)
        .filter(AgentFileModel.agent_id == agent_id)
        .order_by(AgentFileModel.uploaded_at.asc())
        .all()
    )
    file_ids: list[str] = []
    for row in rows:
        disk_path = agent_dir(agent_id) / row.id
        if not disk_path.is_file():
            continue
        openai_id = ensure_openai_file_for_row(db, agent, row, disk_path)
        if openai_id:
            file_ids.append(openai_id)
    return file_ids


def _extract_container_id(response: Any) -> str | None:
    output = getattr(response, "output", None) or []
    for item in output:
        if getattr(item, "type", None) == "code_interpreter_call":
            container_id = getattr(item, "container_id", None)
            if container_id:
                return container_id
    return None


def _build_instructions(agent: AgentModel) -> str:
    role_text = strip_html(agent.role_instructions or "").strip()
    base_rules = (
        "Reglas:\n"
        "- Responde en español.\n"
        "- Usa los archivos del agente disponibles en el code interpreter cuando sea necesario.\n"
        "- Si no encuentras la información en los archivos, dilo claramente.\n"
        "- Cita el nombre del documento cuando uses información de él.\n"
        "- Puedes ejecutar código Python para analizar PDF, Excel, CSV y otros archivos cargados.\n"
        "- Si el usuario pide un informe, tabla o documento exportable, genera un archivo "
        "(PDF, Word o Excel) con el code interpreter y menciona el nombre del archivo generado."
    )
    if role_text:
        return f"{role_text}\n\n{base_rules}"
    return base_rules


def _build_code_interpreter_tool(agent: AgentModel, file_ids: list[str]) -> dict[str, Any]:
    if agent.openai_container_id and not is_container_expired(agent.openai_container_updated_at):
        return {
            "type": "code_interpreter",
            "container": agent.openai_container_id,
        }
    return {
        "type": "code_interpreter",
        "container": {
            "type": "auto",
            "file_ids": file_ids,
            "memory_limit": "4g",
        },
    }


def _finalize_openai_response(
    db: Session,
    agent: AgentModel,
    response: Any,
    file_ids: list[str],
) -> dict[str, Any]:
    container_id = _extract_container_id(response)
    if container_id:
        agent.openai_container_id = container_id
        agent.openai_container_updated_at = _utcnow()
        agent.updated_at = _utcnow()
        db.flush()

    reply = (getattr(response, "output_text", None) or "").strip()
    if not reply:
        reply = "No pude generar una respuesta. Intenta reformular la pregunta."

    response_files: list[dict[str, Any]] = []
    if container_id:
        try:
            from app.backend.services.agent_response_files_service import persist_code_interpreter_outputs

            response_files = persist_code_interpreter_outputs(
                db,
                agent.id,
                response,
                container_id,
                file_ids,
            )
        except Exception as exc:
            logger.warning("No se pudieron guardar archivos de respuesta: %s", exc)

    return {
        "reply": reply,
        "containerId": agent.openai_container_id,
        "openaiFilesUsed": len(file_ids),
        "model": settings.openai_agent_model,
        "responseFiles": response_files,
    }


_STREAM_STEP_LABELS: dict[str, str] = {
    "response.created": "Solicitud enviada al modelo…",
    "response.in_progress": "El modelo está procesando tu consulta…",
    "response.queued": "Tu solicitud está en cola…",
    "response.code_interpreter_call.in_progress": "Preparando el intérprete de código…",
    "response.code_interpreter_call.interpreting": "Ejecutando Python para analizar tus archivos…",
    "response.code_interpreter_call.code_done": "Código listo, corriendo el análisis…",
    "response.code_interpreter_call.completed": "Análisis de archivos completado.",
    "response.output_item.added": "Generando la respuesta…",
    "response.reasoning_summary_text.delta": "Razonando sobre los antecedentes…",
    "response.reasoning_summary_part.added": "Organizando el análisis…",
}


def _step_from_stream_event(event: Any) -> str | None:
    etype = getattr(event, "type", None) or ""
    return _STREAM_STEP_LABELS.get(etype)


def stream_chat_with_openai_responses(
    db: Session,
    agent: AgentModel,
    message: str,
    file_ids: list[str],
):
    """Genera eventos {type: step|text_delta} y al final {type: done, data: ...}."""
    client = get_openai_client()
    tools = [_build_code_interpreter_tool(agent, file_ids)]
    seen_steps: set[str] = set()

    def emit_step(label: str) -> dict[str, Any] | None:
        if label in seen_steps:
            return None
        seen_steps.add(label)
        return {"type": "step", "message": label}

    first_step = emit_step(f"Conectando con {settings.openai_agent_model}…")
    if first_step:
        yield first_step

    with client.responses.stream(
        model=settings.openai_agent_model,
        instructions=_build_instructions(agent),
        input=message,
        tools=tools,
    ) as stream:
        for event in stream:
            step_label = _step_from_stream_event(event)
            if step_label:
                step_event = emit_step(step_label)
                if step_event:
                    yield step_event

            etype = getattr(event, "type", None) or ""
            if etype == "response.output_text.delta":
                delta = getattr(event, "delta", None) or ""
                if delta:
                    yield {"type": "text_delta", "delta": delta}

        response = stream.get_final_response()

    save_step = emit_step("Guardando archivos generados, si los hay…")
    if save_step:
        yield save_step
    result = _finalize_openai_response(db, agent, response, file_ids)
    yield {"type": "done", "data": result}


def chat_with_openai_responses(
    db: Session,
    agent: AgentModel,
    message: str,
    file_ids: list[str],
) -> dict[str, Any]:
    client = get_openai_client()
    tools = [_build_code_interpreter_tool(agent, file_ids)]

    response = client.responses.create(
        model=settings.openai_agent_model,
        instructions=_build_instructions(agent),
        input=message,
        tools=tools,
    )

    return _finalize_openai_response(db, agent, response, file_ids)
