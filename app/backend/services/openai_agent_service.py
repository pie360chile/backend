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
