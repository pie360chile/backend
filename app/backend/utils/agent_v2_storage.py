"""Almacenamiento de archivos Agent v2: {FILES_DIR}/agent_v2/{nombre_agente}/"""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.backend.core.config import settings


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._\u00c0-\u024f\s-]", "_", (value or "").strip())
    cleaned = re.sub(r"\s+", "_", cleaned).strip("._")
    if not cleaned:
        raise ValueError("Nombre inválido.")
    return cleaned[:120]


def _safe_relative_path(path: str) -> str:
    raw = (path or "").replace("\\", "/").strip().strip("/")
    if not raw:
        return ""
    parts: list[str] = []
    for part in raw.split("/"):
        if not part or part in {".", ".."}:
            continue
        parts.append(_safe_segment(part))
    return "/".join(parts)


def files_dir() -> Path:
    return Path(settings.files_dir).resolve()


def agent_v2_root() -> Path:
    root = (files_dir() / "agent_v2").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def agent_folder(agent_name: str) -> Path:
    folder = (agent_v2_root() / _safe_segment(agent_name)).resolve()
    if not str(folder).startswith(str(agent_v2_root())):
        raise ValueError("Ruta de agente no permitida.")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def resolve_target(agent_name: str, relative_path: str = "") -> Path:
    folder = agent_folder(agent_name)
    rel = _safe_relative_path(relative_path)
    target = (folder / rel).resolve() if rel else folder
    if not str(target).startswith(str(folder)):
        raise ValueError("Ruta no permitida.")
    return target


def create_folder(agent_name: str, relative_path: str) -> dict[str, Any]:
    target = resolve_target(agent_name, relative_path)
    target.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "path": relative_path or "", "type": "folder"}


def save_file(agent_name: str, relative_path: str, data: bytes) -> dict[str, Any]:
    if not data:
        raise ValueError("El archivo está vacío.")
    rel = _safe_relative_path(relative_path)
    if not rel:
        raise ValueError("relative_path es obligatorio.")
    target = resolve_target(agent_name, rel)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {
        "ok": True,
        "name": target.name,
        "path": rel,
        "type": "file",
        "size_bytes": target.stat().st_size,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }


def count_files(agent_name: str) -> int:
    folder = agent_folder(agent_name)
    if not folder.exists():
        return 0
    total = 0
    for item in folder.rglob("*"):
        if item.is_file():
            total += 1
    return total


def list_entries(agent_name: str, relative_path: str = "") -> dict[str, Any]:
    current = resolve_target(agent_name, relative_path)
    if not current.exists():
        current.mkdir(parents=True, exist_ok=True)

    rel = _safe_relative_path(relative_path)
    entries: list[dict[str, Any]] = []

    for item in sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        entry_rel = f"{rel}/{item.name}".strip("/") if rel else item.name
        if item.is_dir():
            file_count = sum(1 for f in item.rglob("*") if f.is_file())
            entries.append(
                {
                    "name": item.name,
                    "path": entry_rel,
                    "type": "folder",
                    "fileCount": file_count,
                }
            )
        else:
            entries.append(
                {
                    "name": item.name,
                    "path": entry_rel,
                    "type": "file",
                    "sizeBytes": item.stat().st_size,
                }
            )

    return {
        "path": rel,
        "entries": entries,
        "totalFiles": count_files(agent_name),
    }


def delete_entry(agent_name: str, relative_path: str) -> dict[str, Any]:
    rel = _safe_relative_path(relative_path)
    if not rel:
        raise ValueError("No se puede eliminar la raíz del agente.")
    target = resolve_target(agent_name, rel)
    folder = agent_folder(agent_name)
    if not str(target).startswith(str(folder)) or target == folder:
        raise ValueError("Ruta no permitida.")
    if not target.exists():
        raise ValueError("Archivo o carpeta no encontrado.")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"ok": True, "path": rel}


def rename_agent_folder(old_name: str, new_name: str) -> None:
    old_folder = agent_folder(old_name)
    new_folder = agent_folder(new_name)
    if old_folder == new_folder:
        return
    if new_folder.exists() and any(new_folder.iterdir()):
        raise ValueError("Ya existe una carpeta para el nuevo nombre del agente.")
    if old_folder.exists():
        if new_folder.exists():
            shutil.rmtree(new_folder, ignore_errors=True)
        old_folder.rename(new_folder)


def delete_agent_folder(agent_name: str) -> None:
    folder = agent_folder(agent_name)
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)


def document_template_dir(agent_name: str, document_id: int) -> Path:
    folder = resolve_target(agent_name, f"documentos/{document_id}")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def save_document_template(
    agent_name: str,
    document_id: int,
    data: bytes,
    format_type: str,
) -> dict[str, Any]:
    if not data:
        raise ValueError("El archivo está vacío.")
    fmt = format_type.lower()
    if fmt not in {"docx", "pdf"}:
        raise ValueError("Formato no soportado. Use .docx o .pdf.")
    folder = document_template_dir(agent_name, document_id)
    filename = f"formato.{fmt}"
    target = (folder / filename).resolve()
    if not str(target).startswith(str(agent_folder(agent_name))):
        raise ValueError("Ruta no permitida.")
    target.write_bytes(data)
    rel = str(target.relative_to(files_dir())).replace("\\", "/")
    return {
        "ok": True,
        "filename": filename,
        "relativePath": rel,
        "formatType": fmt,
        "sizeBytes": target.stat().st_size,
    }
