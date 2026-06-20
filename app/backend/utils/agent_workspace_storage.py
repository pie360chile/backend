"""Almacenamiento de informes del Workspace Agent: {FILES_DIR}/agents/{agent_id}/"""

from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.backend.core.config import settings

# Tamaño recomendado por chunk (bytes crudos) para invocaciones MCP con base64.
RECOMMENDED_CHUNK_BYTES = 64 * 1024


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


def uploads_root(agent_id: str) -> Path:
    folder = (agent_folder(agent_id) / ".uploads").resolve()
    if not str(folder).startswith(str(agents_root())):
        raise ValueError("Ruta de uploads no permitida.")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _upload_session_dir(agent_id: str, upload_id: str) -> Path:
    safe_id = _safe_segment(upload_id)
    session = (uploads_root(agent_id) / safe_id).resolve()
    root = uploads_root(agent_id)
    if not str(session).startswith(str(root)):
        raise ValueError("upload_id no permitido.")
    return session


def _load_upload_meta(session_dir: Path) -> dict[str, Any]:
    meta_path = session_dir / "meta.json"
    if not meta_path.exists():
        raise ValueError("Sesión de subida no encontrada.")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def _save_upload_meta(session_dir: Path, meta: dict[str, Any]) -> None:
    (session_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False),
        encoding="utf-8",
    )


def begin_chunked_upload(agent_id: str, filename: str, total_chunks: int) -> dict[str, Any]:
    if total_chunks < 1:
        raise ValueError("total_chunks debe ser >= 1.")
    aid = resolve_agent_id(agent_id)
    fname = _safe_segment(filename.strip())
    upload_id = uuid.uuid4().hex
    session_dir = _upload_session_dir(aid, upload_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "upload_id": upload_id,
        "agent_id": aid,
        "filename": fname,
        "total_chunks": total_chunks,
        "received": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_upload_meta(session_dir, meta)
    return {
        "ok": True,
        "upload_id": upload_id,
        "agent_id": aid,
        "filename": fname,
        "total_chunks": total_chunks,
        "recommended_chunk_bytes": RECOMMENDED_CHUNK_BYTES,
    }


def append_upload_chunk(
    agent_id: str,
    upload_id: str,
    chunk_index: int,
    data: bytes,
) -> dict[str, Any]:
    aid = resolve_agent_id(agent_id)
    session_dir = _upload_session_dir(aid, upload_id)
    if not session_dir.exists():
        raise ValueError("Sesión de subida no encontrada.")
    meta = _load_upload_meta(session_dir)
    total = int(meta["total_chunks"])
    if chunk_index < 0 or chunk_index >= total:
        raise ValueError(f"chunk_index fuera de rango (0-{total - 1}).")
    chunk_path = session_dir / f"chunk_{chunk_index:06d}"
    chunk_path.write_bytes(data)
    received = set(meta.get("received", []))
    received.add(chunk_index)
    meta["received"] = sorted(received)
    _save_upload_meta(session_dir, meta)
    return {
        "ok": True,
        "upload_id": upload_id,
        "agent_id": aid,
        "chunk_index": chunk_index,
        "received_count": len(meta["received"]),
        "total_chunks": total,
        "complete": len(meta["received"]) == total,
    }


def finalize_chunked_upload(agent_id: str, upload_id: str) -> dict[str, Any]:
    aid = resolve_agent_id(agent_id)
    session_dir = _upload_session_dir(aid, upload_id)
    if not session_dir.exists():
        raise ValueError("Sesión de subida no encontrada.")
    meta = _load_upload_meta(session_dir)
    total = int(meta["total_chunks"])
    received = sorted(set(meta.get("received", [])))
    if len(received) != total:
        missing = sorted(set(range(total)) - set(received))
        raise ValueError(f"Faltan chunks: {missing}")
    parts: list[bytes] = []
    for index in range(total):
        chunk_path = session_dir / f"chunk_{index:06d}"
        if not chunk_path.exists():
            raise ValueError(f"Chunk {index} no encontrado en disco.")
        parts.append(chunk_path.read_bytes())
    path = target_file(aid, meta["filename"])
    path.write_bytes(b"".join(parts))
    shutil.rmtree(session_dir, ignore_errors=True)
    return file_result(path, aid, meta["filename"])


def cancel_chunked_upload(agent_id: str, upload_id: str) -> dict[str, Any]:
    aid = resolve_agent_id(agent_id)
    session_dir = _upload_session_dir(aid, upload_id)
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)
    return {"ok": True, "upload_id": upload_id, "agent_id": aid, "cancelled": True}


def save_uploaded_bytes(agent_id: str, filename: str, data: bytes) -> dict[str, Any]:
    aid = resolve_agent_id(agent_id)
    fname = _safe_segment(filename.strip())
    path = target_file(aid, fname)
    path.write_bytes(data)
    return file_result(path, aid, fname)
