"""Rutas en disco para archivos de agentes PIE360."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

AGENT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
AGENTS_ROOT = Path("files/agents")

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".txt",
    ".md",
    ".xlsx",
    ".csv",
}

RESPONSE_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xlsx",
    ".xls",
    ".csv",
}


class AgentFileError(ValueError):
    pass


def validate_agent_id(agent_id: str) -> str:
    if not agent_id or not AGENT_ID_PATTERN.match(agent_id):
        raise AgentFileError("ID de agente inválido")
    return agent_id


def agent_dir(agent_id: str) -> Path:
    return AGENTS_ROOT / validate_agent_id(agent_id)


def ensure_agent_dir(agent_id: str) -> Path:
    directory = agent_dir(agent_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def responses_dir(agent_id: str) -> Path:
    return agent_dir(agent_id) / "responses"


def ensure_responses_dir(agent_id: str) -> Path:
    directory = responses_dir(agent_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def build_response_storage_path(filename: str) -> tuple[str, str]:
    """Devuelve (id relativo responses/..., nombre visible)."""
    safe_leaf = safe_display_name(filename)
    suffix = Path(safe_leaf).suffix.lower()
    if suffix and suffix not in RESPONSE_EXTENSIONS:
        raise AgentFileError(f"Extensión de respuesta no permitida: {suffix}")

    token = uuid.uuid4().hex[:10]
    stored_leaf = f"{token}_{safe_leaf}"
    storage_path = f"responses/{stored_leaf}"
    return storage_path, safe_leaf


def safe_display_name(filename: str | None) -> str:
    raw = Path(filename or "archivo").name.strip()
    cleaned = re.sub(r"[^\w.\- ()áéíóúÁÉÍÓÚñÑ]", "_", raw)
    return cleaned[:200] or "archivo"


def safe_folder_part(name: str) -> str:
    cleaned = re.sub(r"[^\w.\- ()áéíóúÁÉÍÓÚñÑ]", "_", name.strip())
    return cleaned[:100] or "carpeta"


def normalize_upload_path(raw: str | None) -> str:
    if not raw:
        raise AgentFileError("Ruta de archivo inválida")
    normalized = raw.replace("\\", "/").strip().lstrip("/")
    if not normalized or ".." in normalized.split("/"):
        raise AgentFileError("Ruta de archivo inválida")
    return normalized


def build_agent_storage_path(relative_path: str | None) -> tuple[str, str]:
    """Devuelve (ruta relativa en disco, nombre visible)."""
    normalized = normalize_upload_path(relative_path)
    parts = normalized.split("/")
    leaf = parts[-1]
    suffix = Path(leaf).suffix.lower()
    if suffix and suffix not in ALLOWED_EXTENSIONS:
        raise AgentFileError(f"Extensión no permitida: {suffix}")

    safe_leaf = safe_display_name(leaf)
    token = uuid.uuid4().hex[:10]
    stored_leaf = f"{token}_{safe_leaf}"
    if len(parts) == 1:
        storage_path = stored_leaf
    else:
        folder_parts = [safe_folder_part(part) for part in parts[:-1]]
        storage_path = "/".join(folder_parts + [stored_leaf])

    return storage_path, normalized


def validate_stored_filename(stored_name: str) -> str:
    normalized = stored_name.replace("\\", "/").strip().lstrip("/")
    if not normalized or ".." in normalized.split("/"):
        raise AgentFileError("Nombre de archivo inválido")
    if "/" in normalized:
        return normalized
    name = Path(stored_name).name
    if not name or name != stored_name:
        raise AgentFileError("Nombre de archivo inválido")
    return name


def validate_folder_path(folder_path: str) -> str:
    normalized = folder_path.replace("\\", "/").strip().strip("/")
    if not normalized or ".." in normalized.split("/"):
        raise AgentFileError("Ruta de carpeta inválida")
    return normalized


def path_in_folder(path: str, folder_path: str) -> bool:
    normalized = path.replace("\\", "/").strip().strip("/")
    folder = validate_folder_path(folder_path)
    return normalized == folder or normalized.startswith(f"{folder}/")


def file_record(path: Path) -> dict:
    stat = path.stat()
    uploaded_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    display_name = path.name.split("_", 1)[1] if "_" in path.name else path.name
    return {
        "id": path.name,
        "name": display_name,
        "size": stat.st_size,
        "uploadedAt": uploaded_at,
    }


def list_agent_files(agent_id: str) -> list[dict]:
    directory = agent_dir(agent_id)
    if not directory.is_dir():
        return []
    files = [file_record(p) for p in directory.iterdir() if p.is_file()]
    files.sort(key=lambda item: item["uploadedAt"], reverse=True)
    return files
