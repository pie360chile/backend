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


_MIN_MENTIONED_STEM_LEN = 10


def _is_plausible_generated_filename(name: str) -> bool:
    suffix = Path(name).suffix.lower()
    if suffix not in RESPONSE_EXTENSIONS:
        return False
    stem = Path(name).stem.strip()
    if len(stem) < _MIN_MENTIONED_STEM_LEN:
        return False
    return True


def filter_mentioned_filenames(names: set[str]) -> set[str]:
    """Quita fragmentos como Diaz.docx dentro de Informe_Isabella_Diaz.docx."""
    plausible = {name for name in names if _is_plausible_generated_filename(name)}
    if not plausible:
        return set()

    maximal: set[str] = set()
    for name in sorted(plausible, key=len, reverse=True):
        lower = name.lower()
        if any(
            other.lower() != lower and other.lower().endswith(lower)
            for other in maximal
        ):
            continue
        maximal.add(name)
    return maximal


def best_mentioned_filename(names: set[str]) -> str:
    filtered = filter_mentioned_filenames(names)
    if not filtered:
        return ""
    return max(filtered, key=lambda name: len(Path(name).stem))


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
    return filter_mentioned_filenames(names)


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
        blocks: list[Any] = []
        if getattr(item, "type", None) == "message":
            blocks = list(getattr(item, "content", None) or [])
        elif getattr(item, "type", None) == "code_interpreter_call":
            blocks = list(getattr(item, "outputs", None) or [])
        for block in blocks:
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
    normalized = _normalize_name_token(Path(lower).stem)
    if lower.startswith("file-"):
        for display in user_names:
            token = _normalize_name_token(Path(display).stem)
            if len(token) >= 8 and token in normalized:
                return True
    for display in user_names:
        if display.lower() == lower:
            return True
        stem = Path(display).stem.lower()
        if stem and lower.startswith("file-") and stem in lower:
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
    content = client.containers.files.content.retrieve(
        file_id,
        container_id=container_id,
        timeout=120.0,
    )
    return content.read()


def _list_container_generated_citations(
    client: Any,
    container_id: str,
    *,
    user_ids: set[str],
) -> list[dict[str, str]]:
    """Lista archivos del contenedor que no son los uploads del usuario."""
    try:
        page = client.containers.files.list(container_id=container_id, limit=100)
    except Exception as exc:
        logger.warning("No se pudo listar archivos del contenedor %s: %s", container_id, exc)
        return []

    citations: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in getattr(page, "data", None) or []:
        file_id = getattr(row, "id", None)
        if not file_id or file_id in seen or file_id in user_ids:
            continue
        source = (getattr(row, "source", None) or "").lower()
        if source == "user":
            continue
        path = getattr(row, "path", None) or getattr(row, "filename", None) or ""
        filename = Path(str(path)).name if path else ""
        if not filename or not _is_response_document(filename):
            continue
        seen.add(file_id)
        citations.append(
            {
                "container_id": container_id,
                "file_id": file_id,
                "filename": filename,
                "created_at": int(getattr(row, "created_at", 0) or 0),
                "source": source or "generated",
            }
        )
    citations.sort(key=lambda row: row.get("created_at", 0), reverse=True)
    return citations


def _list_assistant_container_citations(
    client: Any,
    container_id: str,
    *,
    user_ids: set[str] | None = None,
) -> list[dict[str, str]]:
    """Fallback cuando el modelo no incluye container_file_citation en el mensaje."""
    return _list_container_generated_citations(
        client,
        container_id,
        user_ids=user_ids or set(),
    )


def _save_response_bytes(
    db: Session,
    agent_id: str,
    *,
    content: bytes,
    display_name: str,
    container_id: str,
    file_id: str,
) -> dict[str, Any] | None:
    if not content:
        return None
    try:
        storage_path, visible_name = build_response_storage_path(display_name)
    except AgentFileError as exc:
        logger.warning("Nombre de respuesta inválido %s: %s", display_name, exc)
        return None

    ensure_responses_dir(agent_id)
    destination = agent_dir(agent_id) / storage_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)

    now = datetime.utcnow()
    row = AgentResponseFileModel(
        id=storage_path,
        agent_id=agent_id,
        display_name=visible_name,
        size_bytes=len(content),
        openai_container_id=container_id,
        openai_file_id=file_id,
        created_at=now,
    )
    db.add(row)
    db.flush()
    return _response_file_dict(row)


def try_capture_from_container(
    db: Session,
    agent_id: str,
    container_id: str,
    user_openai_file_ids: list[str],
    mentioned: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Descarga y guarda el archivo generado en cuanto existe en el contenedor."""
    from app.backend.services.openai_agent_service import get_openai_client

    if not container_id:
        return []

    client = get_openai_client()
    user_ids = set(user_openai_file_ids)
    known_ids = _known_openai_file_ids(db, agent_id)
    user_names = _user_upload_display_names(db, agent_id)
    mention_set = mentioned or set()

    citations = _list_container_generated_citations(client, container_id, user_ids=user_ids)
    picks = _pick_candidates(
        citations,
        user_ids=user_ids,
        known_ids=known_ids,
        user_names=user_names,
        mentioned=mention_set,
    )
    if not picks and citations:
        picks = citations[:MAX_SAVED_FILES_PER_CHAT]

    saved: list[dict[str, Any]] = []
    for meta in picks:
        file_id = meta["file_id"]
        cite_container = meta["container_id"]
        display_name = safe_display_name(meta["filename"])
        try:
            content = _download_container_file(client, cite_container, file_id)
        except Exception as exc:
            logger.warning(
                "Captura temprana: no se pudo descargar %s del contenedor %s: %s",
                file_id,
                cite_container,
                exc,
            )
            continue
        row = _save_response_bytes(
            db,
            agent_id,
            content=content,
            display_name=display_name,
            container_id=cite_container,
            file_id=file_id,
        )
        if row:
            known_ids.add(file_id)
            saved.append(row)
            break
    if saved:
        logger.info(
            "Captura temprana guardó %s para agente %s",
            saved[0]["name"],
            agent_id,
        )
    return saved


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

    if not pool and citations:
        pool = citations[:MAX_SAVED_FILES_PER_CHAT]

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
    *,
    early_saved: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Guarda solo el archivo nuevo que el modelo generó (máx. 1)."""
    if early_saved:
        return early_saved[:MAX_SAVED_FILES_PER_CHAT]

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
    if not citations:
        citations = _list_container_generated_citations(client, container_id, user_ids=user_ids)
        if citations:
            logger.info(
                "persist_code_interpreter_outputs: usando listado del contenedor (agente=%s, n=%s)",
                agent_id,
                len(citations),
            )

    picks = _pick_candidates(
        citations,
        user_ids=user_ids,
        known_ids=known_ids,
        user_names=user_names,
        mentioned=mentioned,
    )

    if not picks:
        logger.warning(
            "persist_code_interpreter_outputs: sin archivo guardable (agente=%s, mencionados=%s, citas=%s)",
            agent_id,
            sorted(mentioned),
            len(citations),
        )
        return []

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

        row = _save_response_bytes(
            db,
            agent_id,
            content=content,
            display_name=display_name,
            container_id=cite_container,
            file_id=file_id,
        )
        if row:
            known_ids.add(file_id)
            saved.append(row)
            break

    return saved
