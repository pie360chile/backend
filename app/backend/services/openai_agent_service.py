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


def sync_agent_openai_files(
    db: Session,
    agent_id: str,
    *,
    only_rows: list[AgentFileModel] | None = None,
) -> list[str]:
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        return []

    if only_rows is not None:
        rows = only_rows
    else:
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


def _extract_container_id(response: Any, agent: AgentModel | None = None) -> str | None:
    from app.backend.services.agent_response_files_service import _extract_container_id_from_response

    container_id = _extract_container_id_from_response(response)
    if container_id:
        return container_id
    if agent and agent.openai_container_id and not is_container_expired(agent.openai_container_updated_at):
        return agent.openai_container_id
    return None


def _agent_uploaded_file_names(db: Session, agent_id: str) -> list[str]:
    rows = (
        db.query(AgentFileModel.display_name)
        .filter(AgentFileModel.agent_id == agent_id)
        .order_by(AgentFileModel.uploaded_at.asc())
        .all()
    )
    return [row[0] for row in rows if row[0]]


def _build_instructions(agent: AgentModel, available_files: list[str] | None = None) -> str:
    role_text = strip_html(agent.role_instructions or "").strip()
    base_rules = (
        "Reglas:\n"
        "- Responde en español.\n"
        "- El ROL DEL AGENTE (texto anterior) tiene prioridad: si ya indica formatos oficiales, "
        "cartilla técnica o estructura del informe, aplícalos aunque el usuario no los repita en el chat.\n"
        "- Usa los archivos del agente disponibles en el code interpreter cuando sea necesario.\n"
        "- Si no encuentras la información en los archivos, dilo claramente.\n"
        "- Cita el nombre del documento cuando uses información de él.\n"
        "- Puedes ejecutar código Python para analizar PDF, Excel, CSV y otros archivos cargados.\n"
        "- Si el usuario pide un informe, tabla o documento exportable, genera UN solo archivo "
        "(preferiblemente Word .docx) con el code interpreter y menciona solo su nombre.\n"
        "- Genera el informe solo para la persona o caso que el usuario pidió; "
        "no generes informes de otros estudiantes que aparezcan en los archivos fuente.\n"
        "- Abre en el code interpreter solo los archivos listados abajo; "
        "no proceses otros estudiantes ni documentos que no correspondan a esta solicitud.\n"
        "- Para un solo estudiante, abre como máximo la plantilla/formato y el archivo de ese caso; "
        "no abras PDFs de otros alumnos ni documentos de referencia que no uses.\n"
        "- Sé eficiente: extrae solo los datos necesarios del informe fuente; "
        "no re-leas ni reproceses archivos que ya no necesitas.\n"
        "- NO incluyas enlaces sandbox:, rutas /mnt/data/ ni URLs de descarga en tu respuesta; "
        "la plataforma mostrará botones de descarga automáticamente.\n"
        "- NUNCA pegues código Python ni logs del intérprete en tu respuesta al usuario; "
        "solo un resumen breve en español y el nombre del archivo generado."
    )
    parts: list[str] = []
    if role_text:
        parts.append(role_text)
    if available_files:
        listing = "\n".join(f"- {name}" for name in available_files[:50])
        parts.append(
            "Archivos cargados del agente (disponibles en el code interpreter):\n"
            f"{listing}"
        )
    parts.append(base_rules)
    return "\n\n".join(parts)


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


def _container_id_from_stream_event(event: Any) -> str | None:
    item = getattr(event, "item", None)
    if item is not None:
        container_id = getattr(item, "container_id", None)
        if container_id:
            return container_id
    return getattr(event, "container_id", None)


def _finalize_openai_response(
    db: Session,
    agent: AgentModel,
    response: Any,
    file_ids: list[str],
    *,
    early_saved: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    container_id = _extract_container_id(response, agent)
    if container_id:
        agent.openai_container_id = container_id
        agent.openai_container_updated_at = _utcnow()
        agent.updated_at = _utcnow()
        db.flush()

    reply = (getattr(response, "output_text", None) or "").strip()
    if not reply:
        reply = "No pude generar una respuesta. Intenta reformular la pregunta."

    response_files: list[dict[str, Any]] = []
    response_files_warning: str | None = None
    if container_id:
        try:
            from app.backend.services.agent_response_files_service import persist_code_interpreter_outputs

            response_files = persist_code_interpreter_outputs(
                db,
                agent.id,
                response,
                container_id,
                file_ids,
                early_saved=early_saved,
            )
        except Exception as exc:
            logger.warning("No se pudieron guardar archivos de respuesta: %s", exc)
            response_files_warning = (
                "No se pudo guardar el archivo generado en el servidor. "
                "Vuelve a pedir el informe o contacta al administrador."
            )

    from app.backend.services.agent_response_files_service import (
        best_mentioned_filename,
        extract_mentioned_filenames,
        sanitize_reply_sandbox_links,
    )

    mentioned = extract_mentioned_filenames(reply)
    best_mentioned = best_mentioned_filename(mentioned)
    if best_mentioned and not response_files and not response_files_warning:
        response_files_warning = (
            f"No se pudo guardar {best_mentioned} en el servidor. "
            "Vuelve a pedir al agente que genere el documento."
        )
    elif response_files:
        response_files_warning = None

    reply = sanitize_reply_sandbox_links(reply, response_files)
    if _is_code_interpreter_dump(reply):
        if response_files:
            names = ", ".join(item["name"] for item in response_files)
            reply = (
                f"Listo. Generé el documento: {names}. "
                "Usa el botón «Descargar» que aparece debajo de este mensaje."
            )
        elif response_files_warning:
            reply = response_files_warning
        else:
            mentioned = extract_mentioned_filenames(reply)
            best_name = best_mentioned_filename(mentioned)
            if best_name:
                reply = (
                    f"Generé el archivo {best_name}, pero no pude guardarlo en el servidor. "
                    "Vuelve a pedir el informe."
                )
            else:
                reply = (
                    "Generé el documento, pero no pude guardarlo en el servidor. "
                    "Vuelve a pedir el informe."
                )
    elif response_files:
        names = ", ".join(item["name"] for item in response_files)
        reply = (
            f"Listo. Generé el documento: {names}. "
            "Usa el botón «Descargar» debajo de este mensaje."
        )

    return {
        "reply": reply,
        "containerId": agent.openai_container_id,
        "openaiFilesUsed": len(file_ids),
        "model": settings.openai_agent_model,
        "responseFiles": response_files,
        "responseFilesWarning": response_files_warning,
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
    "response.output_item.done": "Bloque de respuesta generado…",
    "response.output_text.done": "Texto de respuesta listo…",
    "response.content_part.added": "Escribiendo la respuesta…",
    "response.content_part.done": "Sección de respuesta completada…",
    "response.completed": "Modelo finalizó la generación…",
    "response.reasoning_summary_text.delta": "Razonando sobre los antecedentes…",
    "response.reasoning_summary_part.added": "Organizando el análisis…",
    "response.reasoning_summary_text.done": "Razonamiento completado…",
    "response.reasoning_text.delta": "Elaborando el informe…",
    "response.reasoning_text.done": "Redacción interna completada…",
}

_POST_INTERPRETER_STEP = "Redactando la respuesta final (puede tardar varios minutos)…"


def _step_from_stream_event(event: Any) -> str | None:
    etype = getattr(event, "type", None) or ""
    if etype in _STREAM_STEP_LABELS:
        return _STREAM_STEP_LABELS[etype]
    if "reasoning" in etype:
        return "Elaborando el informe con los datos analizados…"
    return None


def _extract_text_delta(event: Any) -> str:
    """Solo texto final del asistente; nunca logs/código del code interpreter."""
    etype = getattr(event, "type", None) or ""
    if etype in ("response.output_text.delta", "response.text.delta"):
        return getattr(event, "delta", None) or getattr(event, "text", None) or ""
    return ""


def _is_code_interpreter_dump(text: str) -> bool:
    if not text or len(text) < 80:
        return False
    markers = (
        "import ",
        "def ",
        "subprocess.",
        "doc.save(",
        "for p in ",
        "Pt(12)",
        "qn('w:",
        "capture_output=True",
    )
    hits = sum(1 for marker in markers if marker in text)
    return hits >= 2


def stream_chat_with_openai_responses(
    db: Session,
    agent: AgentModel,
    message: str,
    file_ids: list[str],
    instruction_file_names: list[str] | None = None,
):
    """Genera eventos {type: step|text_delta} y al final {type: done, data: ...}."""
    client = get_openai_client()
    tools = [_build_code_interpreter_tool(agent, file_ids)]
    file_names = instruction_file_names or _agent_uploaded_file_names(db, agent.id)
    seen_steps: set[str] = set()
    early_saved: list[dict[str, Any]] = []
    stream_container_id: str | None = agent.openai_container_id

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
        instructions=_build_instructions(agent, file_names),
        input=message,
        tools=tools,
    ) as stream:
        for event in stream:
            etype = getattr(event, "type", None) or ""

            step_label = _step_from_stream_event(event)
            if step_label:
                step_event = emit_step(step_label)
                if step_event:
                    yield step_event

            if etype == "response.code_interpreter_call.completed":
                post_step = emit_step(_POST_INTERPRETER_STEP)
                if post_step:
                    yield post_step
                container_id = _container_id_from_stream_event(event) or stream_container_id
                if container_id:
                    stream_container_id = container_id
                    if not early_saved:
                        from app.backend.services.agent_response_files_service import try_capture_from_container

                        captured = try_capture_from_container(
                            db,
                            agent.id,
                            container_id,
                            file_ids,
                        )
                        if captured:
                            early_saved = captured
                            save_event = emit_step(
                                f"Archivo guardado: {captured[0]['name']}"
                            )
                            if save_event:
                                yield save_event

            if etype == "response.code_interpreter_call.in_progress":
                container_id = _container_id_from_stream_event(event)
                if container_id:
                    stream_container_id = container_id

            delta = _extract_text_delta(event)
            if delta:
                yield {"type": "text_delta", "delta": delta}

        consolidating = emit_step("Consolidando respuesta del modelo…")
        if consolidating:
            yield consolidating
        response = stream.get_final_response()

    save_step = emit_step("Guardando archivos generados, si los hay…")
    if save_step:
        yield save_step
    result = _finalize_openai_response(
        db,
        agent,
        response,
        file_ids,
        early_saved=early_saved or None,
    )
    yield {"type": "done", "data": result}


def chat_with_openai_responses(
    db: Session,
    agent: AgentModel,
    message: str,
    file_ids: list[str],
) -> dict[str, Any]:
    client = get_openai_client()
    tools = [_build_code_interpreter_tool(agent, file_ids)]
    file_names = _agent_uploaded_file_names(db, agent.id)

    response = client.responses.create(
        model=settings.openai_agent_model,
        instructions=_build_instructions(agent, file_names),
        input=message,
        tools=tools,
    )

    return _finalize_openai_response(db, agent, response, file_ids)
