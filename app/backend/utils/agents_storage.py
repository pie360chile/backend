"""Agents file storage: {FILES_DIR}/agents/c{customer_id}/{agent_name}/"""

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
        raise ValueError("Invalid name.")
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


def agents_root() -> Path:
    root = (files_dir() / "agents").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def agent_folder(agent_name: str, customer_id: int | None = None) -> Path:
    root = agents_root()
    name = _safe_segment(agent_name)
    if customer_id:
        base = (root / f"c{int(customer_id)}").resolve()
        base.mkdir(parents=True, exist_ok=True)
        folder = (base / name).resolve()
        if not str(folder).startswith(str(base)):
            raise ValueError("Agent path not allowed.")
    else:
        folder = (root / name).resolve()
        if not str(folder).startswith(str(root)):
            raise ValueError("Agent path not allowed.")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def resolve_target(
    agent_name: str, relative_path: str = "", customer_id: int | None = None
) -> Path:
    folder = agent_folder(agent_name, customer_id)
    rel = _safe_relative_path(relative_path)
    target = (folder / rel).resolve() if rel else folder
    if not str(target).startswith(str(folder)):
        raise ValueError("Path not allowed.")
    return target


def create_folder(
    agent_name: str, relative_path: str, customer_id: int | None = None
) -> dict[str, Any]:
    target = resolve_target(agent_name, relative_path, customer_id)
    target.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "path": relative_path or "", "type": "folder"}


def save_file(
    agent_name: str,
    relative_path: str,
    data: bytes,
    customer_id: int | None = None,
) -> dict[str, Any]:
    if not data:
        raise ValueError("File is empty.")
    rel = _safe_relative_path(relative_path)
    if not rel:
        raise ValueError("relative_path is required.")
    target = resolve_target(agent_name, rel, customer_id)
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


def _is_hidden_entry(name: str) -> bool:
    """Carpetas internas no visibles en Archivos (derivados RAG, etc.)."""
    return name in {"_derived"} or name.startswith(".")


def count_files(agent_name: str, customer_id: int | None = None) -> int:
    folder = agent_folder(agent_name, customer_id)
    if not folder.exists():
        return 0
    total = 0
    for item in folder.rglob("*"):
        if not item.is_file():
            continue
        try:
            rel_parts = item.relative_to(folder).parts
        except ValueError:
            continue
        if any(_is_hidden_entry(p) for p in rel_parts):
            continue
        total += 1
    return total


def list_entries(
    agent_name: str, relative_path: str = "", customer_id: int | None = None
) -> dict[str, Any]:
    current = resolve_target(agent_name, relative_path, customer_id)
    if not current.exists():
        current.mkdir(parents=True, exist_ok=True)

    rel = _safe_relative_path(relative_path)
    entries: list[dict[str, Any]] = []

    for item in sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if _is_hidden_entry(item.name):
            continue
        entry_rel = f"{rel}/{item.name}".strip("/") if rel else item.name
        if item.is_dir():
            file_count = sum(
                1
                for f in item.rglob("*")
                if f.is_file()
                and not any(_is_hidden_entry(p) for p in f.relative_to(item).parts)
            )
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
        "totalFiles": count_files(agent_name, customer_id),
    }


def delete_entry(
    agent_name: str, relative_path: str, customer_id: int | None = None
) -> dict[str, Any]:
    rel = _safe_relative_path(relative_path)
    if not rel:
        raise ValueError("Cannot delete the agent root.")
    target = resolve_target(agent_name, rel, customer_id)
    folder = agent_folder(agent_name, customer_id)
    if not str(target).startswith(str(folder)) or target == folder:
        raise ValueError("Path not allowed.")
    if not target.exists():
        raise ValueError("File or folder not found.")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"ok": True, "path": rel}


def rename_agent_folder(
    old_name: str, new_name: str, customer_id: int | None = None
) -> None:
    old_folder = agent_folder(old_name, customer_id)
    new_folder = agent_folder(new_name, customer_id)
    if old_folder == new_folder:
        return
    if new_folder.exists() and any(new_folder.iterdir()):
        raise ValueError("A folder already exists for the new agent name.")
    if old_folder.exists():
        if new_folder.exists():
            shutil.rmtree(new_folder, ignore_errors=True)
        old_folder.rename(new_folder)


def delete_agent_folder(agent_name: str, customer_id: int | None = None) -> None:
    folder = agent_folder(agent_name, customer_id)
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)


def document_template_dir(
    agent_name: str, document_id: int, customer_id: int | None = None
) -> Path:
    folder = resolve_target(agent_name, f"documentos/{document_id}", customer_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def save_document_template(
    agent_name: str,
    document_id: int,
    data: bytes,
    format_type: str,
    customer_id: int | None = None,
) -> dict[str, Any]:
    if not data:
        raise ValueError("File is empty.")
    fmt = format_type.lower()
    if fmt not in {"docx", "pdf"}:
        raise ValueError("Unsupported format. Use .docx or .pdf.")
    folder = document_template_dir(agent_name, document_id, customer_id)
    filename = f"formato.{fmt}"
    target = (folder / filename).resolve()
    if not str(target).startswith(str(agent_folder(agent_name, customer_id))):
        raise ValueError("Path not allowed.")
    target.write_bytes(data)
    rel = str(target.relative_to(files_dir())).replace("\\", "/")
    return {
        "ok": True,
        "filename": filename,
        "relativePath": rel,
        "formatType": fmt,
        "sizeBytes": target.stat().st_size,
    }
