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


def _ensure_folder_with_status(
    config: DriveSchoolConfig, parent_id: str, name: str
) -> tuple[str, bool]:
    """Devuelve (folder_id, created). created=False si ya existía."""
    existing = _find_child_folder(config, parent_id, name)
    if existing:
        return existing, False
    return _ensure_folder(config, parent_id, name), True


def sync_customer_agent_folders(db) -> dict[str, Any]:
    """
    Bajo la carpeta raíz de Agentes (agents_app_settings):
      {customer_id}/{agent_name}/
    Crea solo si no existe. Un folder por cada agente con customer_id.
    """
    from app.backend.db.models.agent import AgentModel
    from app.backend.utils.school_drive_config import load_agents_global_drive_config

    try:
        config = load_agents_global_drive_config(db)
    except ValueError as exc:
        return {"ok": False, "message": str(exc), "customers": [], "summary": {}}

    agents = (
        db.query(AgentModel)
        .filter(AgentModel.customer_id.isnot(None))
        .order_by(AgentModel.customer_id.asc(), AgentModel.name.asc())
        .all()
    )
    if not agents:
        return {
            "ok": True,
            "message": "No hay agentes con cliente para sincronizar.",
            "customers": [],
            "summary": {
                "customers_touched": 0,
                "customer_folders_created": 0,
                "customer_folders_existing": 0,
                "agent_folders_created": 0,
                "agent_folders_existing": 0,
            },
        }

    by_customer: dict[int, list[Any]] = {}
    for agent in agents:
        cid = int(agent.customer_id)
        by_customer.setdefault(cid, []).append(agent)

    root_id = config.root_folder_id
    customers_out: list[dict[str, Any]] = []
    summary = {
        "customers_touched": 0,
        "customer_folders_created": 0,
        "customer_folders_existing": 0,
        "agent_folders_created": 0,
        "agent_folders_existing": 0,
    }

    for cid, agent_rows in by_customer.items():
        summary["customers_touched"] += 1
        customer_folder_id, customer_created = _ensure_folder_with_status(
            config, root_id, str(cid)
        )
        if customer_created:
            summary["customer_folders_created"] += 1
        else:
            summary["customer_folders_existing"] += 1

        agent_items: list[dict[str, Any]] = []
        for agent in agent_rows:
            name = (agent.name or "").strip() or f"agent-{agent.id}"
            folder_id, created = _ensure_folder_with_status(
                config, customer_folder_id, name
            )
            if created:
                summary["agent_folders_created"] += 1
            else:
                summary["agent_folders_existing"] += 1
            agent_items.append(
                {
                    "agent_id": agent.id,
                    "name": name,
                    "folder_id": folder_id,
                    "created": created,
                }
            )

        customers_out.append(
            {
                "customer_id": cid,
                "folder_id": customer_folder_id,
                "created": customer_created,
                "agents": agent_items,
            }
        )

    return {
        "ok": True,
        "message": (
            f"Sincronizado: {summary['agent_folders_created']} carpetas de agente creadas, "
            f"{summary['agent_folders_existing']} ya existían."
        ),
        "root_folder_id": root_id,
        "customers": customers_out,
        "summary": summary,
    }


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
