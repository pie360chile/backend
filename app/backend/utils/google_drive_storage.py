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
        .list(
            q=query,
            spaces="drive",
            fields="files(id,name)",
            pageSize=1,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
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
    created = (
        service.files()
        .create(body=meta, fields="id", supportsAllDrives=True)
        .execute()
    )
    return created["id"]


def _ensure_folder_with_status(
    config: DriveSchoolConfig, parent_id: str, name: str
) -> tuple[str, bool]:
    """Devuelve (folder_id, created). created=False si ya existía."""
    existing = _find_child_folder(config, parent_id, name)
    if existing:
        return existing, False
    return _ensure_folder(config, parent_id, name), True


def _list_child_folders(config: DriveSchoolConfig, parent_id: str) -> list[dict[str, str]]:
    service = _service_for_config(config)
    folders: list[dict[str, str]] = []
    page_token: str | None = None
    query = (
        f"'{parent_id}' in parents and "
        f"mimeType = '{_FOLDER_MIME}' and trashed = false"
    )
    while True:
        result = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id,name)",
                pageSize=100,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        for f in result.get("files") or []:
            fid = str(f.get("id") or "")
            name = str(f.get("name") or "")
            if fid and name:
                folders.append({"id": fid, "name": name})
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return folders


def _trash_folder(config: DriveSchoolConfig, folder_id: str) -> None:
    service = _service_for_config(config)
    service.files().update(
        fileId=folder_id,
        body={"trashed": True},
        supportsAllDrives=True,
    ).execute()


def _find_child_by_name(
    config: DriveSchoolConfig, parent_id: str, name: str
) -> dict[str, str] | None:
    """Busca archivo o carpeta por nombre exacto bajo parent_id."""
    service = _service_for_config(config)
    safe_name = name.replace("'", "\\'")
    query = (
        f"'{parent_id}' in parents and "
        f"name = '{safe_name}' and trashed = false"
    )
    result = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id,name,mimeType)",
            pageSize=5,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    files = result.get("files") or []
    if not files:
        return None
    # Preferir carpeta si hay colisión nombre archivo/carpeta
    for f in files:
        if f.get("mimeType") == _FOLDER_MIME:
            return {
                "id": str(f["id"]),
                "name": str(f.get("name") or name),
                "mimeType": _FOLDER_MIME,
            }
    f = files[0]
    return {
        "id": str(f["id"]),
        "name": str(f.get("name") or name),
        "mimeType": str(f.get("mimeType") or ""),
    }


def delete_from_agent_folder(
    *,
    db: Any,
    customer_id: int,
    agent_name: str,
    relative_path: str,
) -> dict[str, Any]:
    """Elimina (papelera) archivo o carpeta en Drive: {root}/{customer_id}/{agent_name}/{path}."""
    from app.backend.utils.school_drive_config import load_agents_global_drive_config

    if int(customer_id) < 1:
        raise ValueError("customer_id inválido.")
    posix = Path(relative_path).as_posix().strip("/")
    parts = [p for p in posix.split("/") if p and p not in (".", "..")]
    if not parts:
        raise ValueError("No se puede eliminar la carpeta raíz del agente en Drive.")

    config = load_agents_global_drive_config(db)
    root_id = config.root_folder_id.strip()
    agent_label = (agent_name or "").strip() or f"agent-{customer_id}"

    customer_folder_id = _find_child_folder(config, root_id, str(int(customer_id)))
    if not customer_folder_id:
        return {
            "ok": True,
            "skipped": True,
            "message": "Carpeta de cliente no existe en Drive.",
        }
    agent_folder_id = _find_child_folder(config, customer_folder_id, agent_label)
    if not agent_folder_id:
        return {
            "ok": True,
            "skipped": True,
            "message": "Carpeta del agente no existe en Drive.",
        }

    parent_id = agent_folder_id
    for segment in parts[:-1]:
        found = _find_child_folder(config, parent_id, segment)
        if not found:
            return {
                "ok": True,
                "skipped": True,
                "message": f"Ruta no encontrada en Drive: {posix}",
            }
        parent_id = found

    target = _find_child_by_name(config, parent_id, parts[-1])
    if not target:
        return {
            "ok": True,
            "skipped": True,
            "message": f"Elemento no encontrado en Drive: {posix}",
        }

    try:
        _trash_folder(config, target["id"])
    except Exception as exc:
        raise ValueError(_drive_api_error_message(exc)) from exc

    return {
        "ok": True,
        "skipped": False,
        "file_id": target["id"],
        "name": target["name"],
        "mime_type": target["mimeType"],
        "drive_path": f"{int(customer_id)}/{agent_label}/{posix}",
    }


def _drive_api_error_message(exc: BaseException) -> str:
    text = str(exc)
    lower = text.lower()
    if "storagequotaexceeded" in lower or "storage quota" in lower:
        return (
            "La cuenta de servicio no tiene cuota en My Drive. "
            "Usa una Shared Drive (unidad compartida), agrega la cuenta de servicio "
            "como miembro con permiso de administrador de contenido, y pon el ID "
            "de una carpeta dentro de esa Shared Drive como carpeta raíz de Agentes."
        )
    return text

def sync_customer_agent_folders(db) -> dict[str, Any]:
    """
    Bajo la carpeta raíz de Agentes (agents_app_settings):
      {customer_id}/{agent_name}/
    - Crea carpetas faltantes
    - Elimina (a la papelera) carpetas de agentes que ya no existen en BD
    - Elimina carpetas de cliente numéricas sin agentes
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
        "customer_folders_deleted": 0,
        "agent_folders_created": 0,
        "agent_folders_existing": 0,
        "agent_folders_deleted": 0,
    }

    expected_customer_ids = {str(cid) for cid in by_customer.keys()}

    # 1) Limpiar carpetas de cliente huérfanas bajo la raíz (solo nombres numéricos).
    for child in _list_child_folders(config, root_id):
        name = child["name"]
        if not name.isdigit():
            continue
        if name in expected_customer_ids:
            continue
        try:
            _trash_folder(config, child["id"])
            summary["customer_folders_deleted"] += 1
        except Exception:
            # No abortar el sync completo por un borrado fallido.
            continue

    # 2) Crear / sincronizar por cada cliente con agentes.
    for cid, agent_rows in by_customer.items():
        summary["customers_touched"] += 1
        customer_folder_id, customer_created = _ensure_folder_with_status(
            config, root_id, str(cid)
        )
        if customer_created:
            summary["customer_folders_created"] += 1
        else:
            summary["customer_folders_existing"] += 1

        expected_names = {
            ((agent.name or "").strip() or f"agent-{agent.id}") for agent in agent_rows
        }

        # Borrar carpetas de agente que ya no están en BD.
        deleted_agents: list[dict[str, Any]] = []
        for child in _list_child_folders(config, customer_folder_id):
            if child["name"] in expected_names:
                continue
            try:
                _trash_folder(config, child["id"])
                summary["agent_folders_deleted"] += 1
                deleted_agents.append(
                    {"name": child["name"], "folder_id": child["id"], "deleted": True}
                )
            except Exception:
                continue

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
                "deleted_agents": deleted_agents,
            }
        )

    return {
        "ok": True,
        "message": (
            f"Sincronizado: +{summary['agent_folders_created']} creadas, "
            f"{summary['agent_folders_existing']} existentes, "
            f"-{summary['agent_folders_deleted']} agentes eliminados, "
            f"-{summary['customer_folders_deleted']} clientes sin agentes eliminados."
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
        .create(
            body=body,
            media_body=media,
            fields="id,name,mimeType,size,webViewLink",
            supportsAllDrives=True,
        )
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


def upload_to_agent_folder(
    *,
    db: Any,
    customer_id: int,
    agent_name: str,
    relative_path: str,
    data: bytes,
    mime_type: str | None = None,
) -> dict[str, Any]:
    """Sube un archivo a Drive Agentes: {root}/{customer_id}/{agent_name}/[parent…]/file."""
    from app.backend.utils.school_drive_config import load_agents_global_drive_config

    if not data:
        raise ValueError("El archivo está vacío.")
    if int(customer_id) < 1:
        raise ValueError("customer_id inválido.")

    config = load_agents_global_drive_config(db)
    root_id = config.root_folder_id.strip()
    agent_label = (agent_name or "").strip() or f"agent-{customer_id}"

    try:
        customer_folder_id = _ensure_folder(config, root_id, str(int(customer_id)))
        agent_folder_id = _ensure_folder(config, customer_folder_id, agent_label)

        posix = Path(relative_path).as_posix().strip("/")
        parts = [p for p in posix.split("/") if p and p not in (".", "..")]
        if not parts:
            raise ValueError("Ruta de archivo inválida.")

        parent_id = agent_folder_id
        for segment in parts[:-1]:
            parent_id = _ensure_folder(config, parent_id, segment)
        name = _safe_filename(parts[-1])

        service = _service_for_config(config)
        try:
            from googleapiclient.http import MediaIoBaseUpload
        except ImportError as exc:
            raise ValueError("googleapiclient no está instalado.") from exc

        # Archivos grandes: upload resumable (evita timeouts y límites multipart).
        resumable = len(data) >= 5 * 1024 * 1024
        media = MediaIoBaseUpload(
            io.BytesIO(data),
            mimetype=mime_type or "application/octet-stream",
            resumable=resumable,
        )

        body = {"name": name, "parents": [parent_id]}
        created = (
            service.files()
            .create(
                body=body,
                media_body=media,
                fields="id,name,mimeType,size,webViewLink",
                supportsAllDrives=True,
            )
            .execute()
        )
    except Exception as exc:
        raise ValueError(_drive_api_error_message(exc)) from exc

    logical = f"{int(customer_id)}/{agent_label}/{'/'.join(parts[:-1] + [name])}".replace(
        "//", "/"
    )
    return {
        "ok": True,
        "file_id": created.get("id"),
        "filename": created.get("name") or name,
        "mime_type": created.get("mimeType"),
        "size_bytes": int(created.get("size") or len(data)),
        "web_view_link": created.get("webViewLink"),
        "drive_path": logical,
        "customer_id": int(customer_id),
        "agent_name": agent_label,
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
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
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
