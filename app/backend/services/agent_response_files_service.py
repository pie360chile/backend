"""Persistir archivos generados por el code interpreter de OpenAI."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.backend.db.models import AgentFileModel, AgentResponseFileModel
from app.backend.utils.agent_files import (
    AgentFileError,
    agent_dir,
    build_response_storage_path,
    ensure_responses_dir,
    RESPONSE_EXTENSIONS,
    safe_display_name,
)

logger = logging.getLogger(__name__)

MAX_SAVED_FILES_PER_CHAT = 1

_SANDBOX_PATH_RE = re.compile(
    r"(?:sandbox:)?/mnt/data/([^\s\)\]\"']+)",
    re.IGNORECASE,
)
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


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


def extract_filenames_from_response_output(response: Any) -> set[str]:
    """Solo nombres citados en la respuesta al usuario, no en logs/código interno."""
    names: set[str] = set()
    output = getattr(response, "output", None) or []
    for item in output:
        if getattr(item, "type", None) != "message":
            continue
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


def _extract_container_id_from_response(response: Any) -> str | None:
    output = getattr(response, "output", None) or []
    for item in output:
        if getattr(item, "type", None) == "code_interpreter_call":
            container_id = getattr(item, "container_id", None)
            if container_id:
                return container_id
    for cite in _extract_container_citations(response):
        if cite.get("container_id"):
            return cite["container_id"]
    return None


def _user_upload_display_names(db: Session, agent_id: str) -> set[str]:
    rows = (
        db.query(AgentFileModel.display_name)
        .filter(AgentFileModel.agent_id == agent_id)
        .all()
    )
    return {row[0] for row in rows if row[0]}


def _normalize_name_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _is_user_upload_mirror(filename: str, user_names: set[str]) -> bool:
    """Detecta copias en el contenedor de archivos que el usuario ya subió."""
    lower = filename.lower()
    if lower.startswith("file-"):
        for display in user_names:
            stem = Path(display).stem
            token = _normalize_name_token(stem)
            if len(token) >= 8 and token in _normalize_name_token(lower):
                return True
    for display in user_names:
        if display.lower() == lower:
            return True
        stem = Path(display).stem.lower()
        if stem and stem in lower and lower.startswith("file-"):
            return True
    return False


def _filename_matches_mention(filename: str, mentioned: set[str]) -> bool:
    if not mentioned:
        return False
    lower = filename.lower()
    stem = Path(lower).stem
    for name in mentioned:
        n = name.lower()
        n_stem = Path(n).stem
        if lower == n or lower.endswith(f"_{n}"):
            return True
        if n_stem and (n_stem in stem or stem in n_stem):
            return True
    return False


def _candidate_score(filename: str, mentioned: set[str]) -> int:
    lower = filename.lower()
    score = 0
    if lower.endswith(".docx"):
        score += 20
    elif lower.endswith(".pdf"):
        score += 10
    if _filename_matches_mention(filename, mentioned):
        score += 40
    if lower.startswith("informe"):
        score += 8
    if lower.startswith("file-"):
        score -= 30
    if "formato" in lower or "cuestionario" in lower or "cartilla" in lower:
        score -= 50
    return score


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


def _pick_candidates(
    citations: list[dict[str, str]],
    *,
    user_ids: set[str],
    known_ids: set[str],
    user_names: set[str],
    mentioned: set[str],
) -> list[dict[str, str]]:
    pool: list[dict[str, str]] = []
    for cite in citations:
        file_id = cite["file_id"]
        filename = cite.get("filename") or "archivo"
        if file_id in user_ids or file_id in known_ids:
            continue
        if _is_user_upload_mirror(filename, user_names):
            continue
        if not _is_response_document(filename):
            continue
        pool.append(cite)

    if not pool:
        return []

    pool.sort(key=lambda row: _candidate_score(row.get("filename") or "", mentioned), reverse=True)
    return pool[:MAX_SAVED_FILES_PER_CHAT]


def persist_code_interpreter_outputs(
    db: Session,
    agent_id: str,
    response: Any,
    container_id: str | None,
    user_openai_file_ids: list[str],
) -> list[dict[str, Any]]:
    """Guarda solo el archivo nuevo que el modelo citó en esta respuesta (máx. 1)."""
    from app.backend.services.openai_agent_service import get_openai_client

    container_id = container_id or _extract_container_id_from_response(response)
    if not container_id:
        logger.warning("persist_code_interpreter_outputs: sin container_id para agente %s", agent_id)
        return []

    client = get_openai_client()
    known_ids = _known_openai_file_ids(db, agent_id)
    user_ids = set(user_openai_file_ids)
    user_names = _user_upload_display_names(db, agent_id)
    mentioned = extract_filenames_from_response_output(response)
    citations = _extract_container_citations(response)

    picks = _pick_candidates(
        citations,
        user_ids=user_ids,
        known_ids=known_ids,
        user_names=user_names,
        mentioned=mentioned,
    )

    if not picks:
        logger.info(
            "persist_code_interpreter_outputs: sin archivo nuevo citado (agente=%s, mencionados=%s)",
            agent_id,
            sorted(mentioned),
        )
        return []

    ensure_responses_dir(agent_id)
    saved: list[dict[str, Any]] = []

    for meta in picks:
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
