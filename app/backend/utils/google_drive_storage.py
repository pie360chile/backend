"""Subida de archivos a Google Drive (credenciales por colegio en settings)."""

from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from app.backend.utils.school_drive_config import DriveSchoolConfig

DRIVE_SCOPES = ("https://www.googleapis.com/auth/drive",)
_FOLDER_MIME = "application/vnd.google-apps.folder"
FLOW_ENTRY = "entry"
FLOW_EXIT = "exit"
DriveFlow = Literal["entry", "exit"]

_LEGACY_FLOW = {"entrada": FLOW_ENTRY, "salida": FLOW_EXIT, "input": FLOW_ENTRY, "output": FLOW_EXIT}


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", (value or "").strip())
    if not cleaned:
        raise ValueError("Segmento de ruta inválido.")
    return cleaned


def _normalize_flow(flow: str) -> DriveFlow:
    key = (flow or FLOW_ENTRY).strip().lower()
    key = _LEGACY_FLOW.get(key, key)
    if key not in (FLOW_ENTRY, FLOW_EXIT):
        raise ValueError("flow debe ser 'entry' o 'exit'.")
    return key  # type: ignore[return-value]


def _normalize_year(year: int | None) -> int:
    value = year if year is not None else datetime.now(timezone.utc).year
    if value < 2000 or value > 2100:
        raise ValueError("year inválido.")
    return int(value)


@lru_cache(maxsize=32)
def _drive_service(cache_key: str, service_account_json: str):
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise ValueError(
            "Faltan dependencias Google Drive. Instala: "
            "google-api-python-client google-auth"
        ) from exc

    import json

    info = json.loads(service_account_json)
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=list(DRIVE_SCOPES),
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _service_for_config(config: DriveSchoolConfig):
    import json

    sa_json = json.dumps(config.service_account_info, sort_keys=True)
    return _drive_service(config.cache_key, sa_json)


def _find_child_folder(config: DriveSchoolConfig, parent_id: str, name: str) -> str | None:
    service = _service_for_config(config)
    safe_name = name.replace("'", "\\'")
    query = (
        f"'{parent_id}' in parents and "
        f"name = '{safe_name}' and "
        f"mimeType = '{_FOLDER_MIME}' and trashed = false"
    )
    result = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id,name)", pageSize=1)
        .execute()
    )
    files = result.get("files") or []
    return files[0]["id"] if files else None


def _ensure_folder(config: DriveSchoolConfig, parent_id: str, name: str) -> str:
    existing = _find_child_folder(config, parent_id, name)
    if existing:
        return existing
    service = _service_for_config(config)
    meta = {
        "name": name,
        "mimeType": _FOLDER_MIME,
        "parents": [parent_id],
    }
    created = service.files().create(body=meta, fields="id").execute()
    return created["id"]


def resolve_target_folder(
    *,
    config: DriveSchoolConfig,
    school_id: int,
    year: int | None,
    flow: str,
    document_id: int,
    student_id: int,
) -> tuple[str, str]:
    """Crea la jerarquía si no existe y devuelve (folder_id, ruta lógica).

    Ruta: {school_id}/{year}/{entry|exit}/{document_id}/{student_id}/
    """
    if document_id < 1:
        raise ValueError("document_id debe ser >= 1.")
    if student_id < 1:
        raise ValueError("student_id debe ser >= 1.")

    root_id = config.root_folder_id.strip()
    y = _normalize_year(year)
    flow_key = _normalize_flow(flow)

    school_seg = _safe_segment(str(school_id))
    year_seg = _safe_segment(str(y))
    doc_seg = _safe_segment(str(document_id))
    student_seg = _safe_segment(str(student_id))

    parent = root_id
    for segment in (school_seg, year_seg, flow_key, doc_seg, student_seg):
        parent = _ensure_folder(config, parent, segment)

    logical = f"{school_seg}/{year_seg}/{flow_key}/{doc_seg}/{student_seg}"
    return parent, logical


def _safe_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    if not name or name in (".", ".."):
        raise ValueError("Nombre de archivo inválido.")
    return name.replace("/", "_").replace("\\", "_")


def upload_bytes(
    *,
    config: DriveSchoolConfig,
    school_id: int,
    year: int | None,
    flow: str,
    document_id: int,
    student_id: int,
    filename: str,
    data: bytes,
    mime_type: str | None = None,
) -> dict[str, Any]:
    if not data:
        raise ValueError("El archivo está vacío.")
    name = _safe_filename(filename)
    folder_id, logical_path = resolve_target_folder(
        config=config,
        school_id=school_id,
        year=year,
        flow=flow,
        document_id=document_id,
        student_id=student_id,
    )
    service = _service_for_config(config)

    try:
        from googleapiclient.http import MediaIoBaseUpload

        media = MediaIoBaseUpload(
            io.BytesIO(data),
            mimetype=mime_type or "application/octet-stream",
            resumable=False,
        )
    except ImportError as exc:
        raise ValueError("googleapiclient no está instalado.") from exc

    body = {"name": name, "parents": [folder_id]}
    created = (
        service.files()
        .create(body=body, media_body=media, fields="id,name,mimeType,size,webViewLink")
        .execute()
    )
    y = _normalize_year(year)
    flow_key = _normalize_flow(flow)
    return {
        "ok": True,
        "file_id": created.get("id"),
        "filename": created.get("name") or name,
        "mime_type": created.get("mimeType"),
        "size_bytes": int(created.get("size") or len(data)),
        "web_view_link": created.get("webViewLink"),
        "drive_path": f"{logical_path}/{name}",
        "school_id": school_id,
        "year": y,
        "flow": flow_key,
        "document_id": document_id,
        "student_id": student_id,
        "drive_config_source": config.source,
    }


def list_folder_files(
    *,
    config: DriveSchoolConfig,
    school_id: int,
    year: int | None,
    flow: str,
    document_id: int,
    student_id: int,
    page_size: int = 50,
) -> dict[str, Any]:
    folder_id, logical_path = resolve_target_folder(
        config=config,
        school_id=school_id,
        year=year,
        flow=flow,
        document_id=document_id,
        student_id=student_id,
    )
    service = _service_for_config(config)
    result = (
        service.files()
        .list(
            q=f"'{folder_id}' in parents and trashed = false",
            spaces="drive",
            fields="files(id,name,mimeType,size,webViewLink,createdTime,modifiedTime)",
            pageSize=min(max(page_size, 1), 100),
            orderBy="modifiedTime desc",
        )
        .execute()
    )
    files = result.get("files") or []
    y = _normalize_year(year)
    flow_key = _normalize_flow(flow)
    return {
        "ok": True,
        "school_id": school_id,
        "year": y,
        "flow": flow_key,
        "document_id": document_id,
        "student_id": student_id,
        "drive_path": logical_path,
        "drive_config_source": config.source,
        "files": files,
    }
