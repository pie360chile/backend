"""Almacenamiento de informes del Workspace Agent: {FILES_DIR}/agents/{agent_id}/"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from app.backend.core.config import settings


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", (value or "").strip())
    if not cleaned:
        raise ValueError("Identificador de agente o nombre de archivo inválido.")
    return cleaned


def files_dir() -> Path:
    return Path(settings.files_dir).resolve()


def agents_root() -> Path:
    root = files_dir() / "agents"
    root.mkdir(parents=True, exist_ok=True)
    return root


def default_agent_id() -> str:
    return _safe_segment(settings.workspace_agent_id)


def resolve_agent_id(agent_id: str | None) -> str:
    value = (agent_id or "").strip() or settings.workspace_agent_id
    return _safe_segment(value)


def agent_folder(agent_id: str) -> Path:
    folder = (agents_root() / resolve_agent_id(agent_id)).resolve()
    if not str(folder).startswith(str(agents_root())):
        raise ValueError("Ruta de agente no permitida.")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def target_file(agent_id: str, filename: str) -> Path:
    folder = agent_folder(agent_id)
    path = (folder / _safe_segment(filename)).resolve()
    if not str(path).startswith(str(folder)):
        raise ValueError("Ruta de archivo no permitida.")
    return path


def file_result(path: Path, agent_id: str, filename: str) -> dict:
    return {
        "ok": True,
        "agent_id": agent_id,
        "filename": filename,
        "path": str(path),
        "relative_path": str(path.relative_to(files_dir())).replace("\\", "/"),
        "size_bytes": path.stat().st_size,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }


def list_agent_files(agent_id: str) -> list[dict]:
    folder = agent_folder(agent_id)
    if not folder.exists():
        return []
    return [
        {
            "name": item.name,
            "path": str(item),
            "size_bytes": item.stat().st_size,
        }
        for item in sorted(folder.iterdir())
        if item.is_file()
    ]
