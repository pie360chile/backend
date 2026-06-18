"""Persistir archivos generados por el code interpreter de OpenAI."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.backend.db.models import AgentResponseFileModel
from app.backend.utils.agent_files import (
    AgentFileError,
    agent_dir,
    build_response_storage_path,
    ensure_responses_dir,
    RESPONSE_EXTENSIONS,
    safe_display_name,
)

logger = logging.getLogger(__name__)


def _response_file_dict(row: AgentResponseFileModel) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.display_name,
        "size": int(row.size_bytes or 0),
        "createdAt": row.created_at.isoformat() if row.created_at else None,
    }


def _is_response_document(filename: str) -> bool:
    suffix = Path(filename).suffix.lower()
    return bool(suffix and suffix in RESPONSE_EXTENSIONS)


_SANDBOX_PATH_RE = re.compile(
    r"(?:sandbox:)?/mnt/data/([^\s\)\]\"']+)",
    re.IGNORECASE,
)
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def extract_mentioned_filenames(text: str) -> set[str]:
    """Nombres de archivo citados en texto del modelo (sandbox, rutas, etc.)."""
    names: set[str] = set()
    if not text:
        return names
    for match in _SANDBOX_PATH_RE.finditer(text):
        names.add(Path(match.group(1)).name)
    for match in re.finditer(
        r"([A-Za-z0-9áéíóúÁÉÍÓÚñÑ_\-.]+?\.(?:pdf|docx?|xlsx?|csv))",
        text,
        re.IGNORECASE,
    ):
        names.add(match.group(1))
    return names


def extract_filenames_from_response(response: Any) -> set[str]:
    names: set[str] = set()
    output = getattr(response, "output", None) or []
    for item in output:
        item_type = getattr(item, "type", None)
        if item_type == "code_interpreter_call":
            for attr in ("outputs", "output", "logs", "code"):
                chunk = getattr(item, attr, None)
                if isinstance(chunk, str):
                    names.update(extract_mentioned_filenames(chunk))
                elif isinstance(chunk, list):
                    for part in chunk:
                        if isinstance(part, str):
                            names.update(extract_mentioned_filenames(part))
                        else:
                            text = getattr(part, "text", None) or getattr(part, "logs", None)
                            if isinstance(text, str):
                                names.update(extract_mentioned_filenames(text))
        if item_type == "message":
            for block in getattr(item, "content", None) or []:
                text = getattr(block, "text", None) or ""
                names.update(extract_mentioned_filenames(text))
    names.update(extract_mentioned_filenames(getattr(response, "output_text", None) or ""))
    return names


def sanitize_reply_sandbox_links(reply: str, response_files: list[dict[str, Any]]) -> str:
    """Quita enlaces sandbox del texto; el usuario descarga con los botones de la UI."""
    if not reply:
        return reply

    by_name = {f["name"].lower(): f["name"] for f in response_files}

    def replace_markdown_link(match: re.Match[str]) -> str:
        label = match.group(1).strip()
        url = match.group(2).strip()
        if not (url.startswith("sandbox:") or "/mnt/data/" in url):
            return match.group(0)
        filename = Path(url.rstrip("/").split("/")[-1]).name
        visible = by_name.get(filename.lower(), filename)
        return f"Archivo generado: {visible} (usa el botón de descarga debajo)"

    cleaned = _MARKDOWN_LINK_RE.sub(replace_markdown_link, reply)
    cleaned = _SANDBOX_PATH_RE.sub("", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _extract_container_citations(response: Any) -> list[dict[str, str]]:
    citations: list[dict[str, str]] = []
    seen: set[str] = set()
    output = getattr(response, "output", None) or []
    for item in output:
        if getattr(item, "type", None) != "message":
            continue
        for block in getattr(item, "content", None) or []:
            if getattr(block, "type", None) != "output_text":
                continue
            for ann in getattr(block, "annotations", None) or []:
                if getattr(ann, "type", None) != "container_file_citation":
                    continue
                file_id = getattr(ann, "file_id", None)
                container_id = getattr(ann, "container_id", None)
                filename = getattr(ann, "filename", None) or "archivo"
                if not file_id or not container_id or file_id in seen:
                    continue
                seen.add(file_id)
                citations.append(
                    {
                        "container_id": container_id,
                        "file_id": file_id,
                        "filename": filename,
                    }
                )
    return citations


def _list_container_files(client: Any, container_id: str) -> list[Any]:
    collected: list[Any] = []
    after: str | None = None
    while True:
        page = client.containers.files.list(
            container_id,
            limit=100,
            order="desc",
            **({"after": after} if after else {}),
        )
        collected.extend(page.data)
        if not getattr(page, "has_more", False):
            break
        if not page.data:
            break
        after = page.data[-1].id
    return collected


def _filename_matches_mention(filename: str, mentioned: set[str]) -> bool:
    if not mentioned:
        return False
    lower = filename.lower()
    for name in mentioned:
        if lower == name.lower() or lower.endswith(f"_{name.lower()}"):
            return True
    return False


def _known_openai_file_ids(db: Session, agent_id: str) -> set[str]:
    rows = (
        db.query(AgentResponseFileModel.openai_file_id)
        .filter(
            AgentResponseFileModel.agent_id == agent_id,
            AgentResponseFileModel.openai_file_id.isnot(None),
        )
        .all()
    )
    return {row[0] for row in rows if row[0]}


def _download_container_file(client: Any, container_id: str, file_id: str) -> bytes:
    content = client.containers.files.content.retrieve(file_id, container_id=container_id)
    return content.read()


def persist_code_interpreter_outputs(
    db: Session,
    agent_id: str,
    response: Any,
    container_id: str | None,
    user_openai_file_ids: list[str],
) -> list[dict[str, Any]]:
    """Descarga PDF/Excel/Word generados y los guarda en files/agents/{id}/responses/."""
    from app.backend.services.openai_agent_service import get_openai_client

    if not container_id:
        return []

    client = get_openai_client()
    known_ids = _known_openai_file_ids(db, agent_id)
    user_ids = set(user_openai_file_ids)
    mentioned_names = extract_filenames_from_response(response)
    candidates: dict[str, dict[str, str]] = {}

    for cite in _extract_container_citations(response):
        if cite["file_id"] in user_ids or cite["file_id"] in known_ids:
            continue
        if not _is_response_document(cite["filename"]):
            continue
        candidates[cite["file_id"]] = cite

    try:
        for item in _list_container_files(client, container_id):
            file_id = getattr(item, "id", None)
            if not file_id or file_id in user_ids or file_id in known_ids:
                continue
            path = getattr(item, "path", None) or ""
            filename = Path(path).name if path else file_id
            is_document = _is_response_document(filename)
            is_mentioned = _filename_matches_mention(filename, mentioned_names)
            if not is_document and not is_mentioned:
                continue
            if file_id not in candidates:
                candidates[file_id] = {
                    "container_id": container_id,
                    "file_id": file_id,
                    "filename": filename,
                }
    except Exception as exc:
        logger.warning("No se pudieron listar archivos del contenedor %s: %s", container_id, exc)

    if not candidates:
        return []

    ensure_responses_dir(agent_id)
    saved: list[dict[str, Any]] = []

    for meta in candidates.values():
        file_id = meta["file_id"]
        cite_container = meta["container_id"]
        display_name = safe_display_name(meta["filename"])
        try:
            content = _download_container_file(client, cite_container, file_id)
        except Exception as exc:
            logger.warning("No se pudo descargar archivo %s del contenedor: %s", file_id, exc)
            continue

        try:
            storage_path, visible_name = build_response_storage_path(display_name)
        except AgentFileError:
            continue

        destination = agent_dir(agent_id) / storage_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

        now = datetime.utcnow()
        row = AgentResponseFileModel(
            id=storage_path,
            agent_id=agent_id,
            display_name=visible_name,
            size_bytes=len(content),
            openai_container_id=cite_container,
            openai_file_id=file_id,
            created_at=now,
        )
        db.add(row)
        db.flush()
        known_ids.add(file_id)
        saved.append(_response_file_dict(row))

    return saved
