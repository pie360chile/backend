"""Subida de archivos a Google Drive (credenciales por customer)."""

from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from app.backend.utils.customer_drive_config import DriveCustomerConfig

# Alias compat
DriveSchoolConfig = DriveCustomerConfig

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


@lru_cache(maxsize=32)
def _drive_service_oauth(cache_key: str, oauth_json: str):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise ValueError(
            "Faltan dependencias Google Drive. Instala: "
            "google-api-python-client google-auth"
        ) from exc

    import json

    info = json.loads(oauth_json)
    creds = Credentials(
        token=info.get("token"),
        refresh_token=info.get("refresh_token"),
        token_uri=info.get("token_uri") or "https://oauth2.googleapis.com/token",
        client_id=info.get("client_id"),
        client_secret=info.get("client_secret"),
        scopes=list(DRIVE_SCOPES),
    )
    if not creds.valid:
        if creds.expired or not creds.token:
            if not creds.refresh_token:
                raise ValueError(
                    "El access_token expiró y no hay refresh_token. "
                    "Genera un nuevo refresh_token OAuth para este cliente."
                )
            creds.refresh(Request())
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _service_for_config(config: DriveSchoolConfig):
    import json

    if getattr(config, "oauth_info", None):
        return _drive_service_oauth(
            config.cache_key,
            json.dumps(config.oauth_info, sort_keys=True),
        )
    if not config.service_account_info:
        raise ValueError("Drive sin credenciales (OAuth o service account).")
    return _drive_service(
        config.cache_key,
        json.dumps(config.service_account_info, sort_keys=True),
    )


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
    """Elimina (papelera) archivo o carpeta en Drive del customer: {root}/{agent_name}/{path}."""
    from app.backend.utils.customer_drive_config import load_customer_drive_config

    if int(customer_id) < 1:
        raise ValueError("customer_id inválido.")
    posix = Path(relative_path).as_posix().strip("/")
    parts = [p for p in posix.split("/") if p and p not in (".", "..")]
    if not parts:
        raise ValueError("No se puede eliminar la carpeta raíz del agente en Drive.")

    config = load_customer_drive_config(db, int(customer_id))
    root_id = config.root_folder_id.strip()
    agent_label = (agent_name or "").strip() or f"agent-{customer_id}"

    agent_folder_id = _find_child_folder(config, root_id, agent_label)
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

def sync_customer_agent_folders(db, customer_id: int | None = None) -> dict[str, Any]:
    """
    En el Drive del customer: {root}/{agent_name}/
    Si customer_id es None, sincroniza cada customer que tenga Drive configurado.
    """
    from app.backend.db.models.agent import AgentModel
    from app.backend.utils.customer_drive_config import (
        customer_drive_configured,
        load_customer_drive_config,
    )

    agents_q = db.query(AgentModel).filter(AgentModel.customer_id.isnot(None))
    if customer_id is not None and int(customer_id) > 0:
        agents_q = agents_q.filter(AgentModel.customer_id == int(customer_id))
    agents = agents_q.order_by(AgentModel.customer_id.asc(), AgentModel.name.asc()).all()

    by_customer: dict[int, list[Any]] = {}
    for agent in agents:
        cid = int(agent.customer_id)
        by_customer.setdefault(cid, []).append(agent)

    if customer_id is not None and int(customer_id) > 0 and int(customer_id) not in by_customer:
        by_customer[int(customer_id)] = []

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

    for cid, agent_list in sorted(by_customer.items()):
        if not customer_drive_configured(db, cid):
            customers_out.append(
                {
                    "customer_id": cid,
                    "ok": False,
                    "message": "Drive no configurado para este customer.",
                    "agents": [],
                }
            )
            continue
        try:
            config = load_customer_drive_config(db, cid)
        except ValueError as exc:
            customers_out.append(
                {"customer_id": cid, "ok": False, "message": str(exc), "agents": []}
            )
            continue

        summary["customers_touched"] += 1
        root_id = config.root_folder_id
        wanted_names = {(a.name or "").strip() for a in agent_list if (a.name or "").strip()}

        for child in _list_child_folders(config, root_id):
            name = child.get("name") or ""
            if name not in wanted_names and name:
                try:
                    _trash_folder(config, child["id"])
                    summary["agent_folders_deleted"] += 1
                except Exception:
                    pass

        agent_rows: list[dict[str, Any]] = []
        for agent in agent_list:
            name = (agent.name or "").strip()
            if not name:
                continue
            folder_id, created = _ensure_folder_with_status(config, root_id, name)
            if created:
                summary["agent_folders_created"] += 1
            else:
                summary["agent_folders_existing"] += 1
            agent_rows.append(
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
                "ok": True,
                "folder_id": root_id,
                "created": False,
                "agents": agent_rows,
            }
        )

    return {
        "ok": True,
        "message": (
            f"Sincronizado por customer: +{summary['agent_folders_created']} creadas, "
            f"{summary['agent_folders_existing']} existentes, "
            f"-{summary['agent_folders_deleted']} eliminadas."
        ),
        "root_folder_id": None,
        "summary": summary,
        "customers": customers_out,
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


def _drive_folder_label(value: str, *, fallback: str = "Sin nombre") -> str:
    """Nombre de carpeta legible (conserva espacios/acentos; sin separadores de ruta)."""
    text = (value or "").strip()
    text = text.replace("/", "-").replace("\\", "-").replace("\0", "")
    text = re.sub(r"\s+", " ", text).strip()
    return (text[:200] if text else fallback)


def _numeric_rut(rut: str) -> str:
    """RUT solo alfanumérico (sin puntos ni guión), p. ej. 274309032."""
    cleaned = re.sub(r"[^0-9kK]", "", (rut or "").strip())
    if not cleaned:
        raise ValueError("RUT del alumno no disponible o inválido.")
    return cleaned.upper()


def _find_child_file(config: DriveSchoolConfig, parent_id: str, name: str) -> str | None:
    service = _service_for_config(config)
    safe_name = name.replace("'", "\\'")
    query = (
        f"'{parent_id}' in parents and "
        f"name = '{safe_name}' and "
        f"mimeType != '{_FOLDER_MIME}' and trashed = false"
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


def upload_student_document_tree(
    *,
    db: Any,
    customer_id: int,
    school_name: str,
    year: int,
    course_name: str,
    student_rut: str,
    document_type_name: str,
    data: bytes,
    file_extension: str,
    mime_type: str | None = None,
) -> dict[str, Any]:
    """
    Sube a Drive del customer con árbol:
      {root}/{Liceo}/{Año}/{Curso}/{RUT numérico}/{RUT_Tipo de documento}.{ext}
    Crea carpetas si no existen. Si el archivo ya existe, lo reemplaza.
    """
    from app.backend.utils.customer_drive_config import (
        customer_drive_configured,
        load_customer_drive_config,
    )

    if not data:
        raise ValueError("El archivo está vacío.")
    if int(customer_id) < 1:
        raise ValueError("customer_id inválido.")
    if not customer_drive_configured(db, int(customer_id)):
        raise ValueError(
            "Google Drive no está configurado para este cliente. "
            "Conéctalo en Configuración → Google Drive."
        )

    config = load_customer_drive_config(db, int(customer_id))
    root_id = config.root_folder_id.strip()
    rut_num = _numeric_rut(student_rut)
    year_label = str(int(year))
    if int(year) < 2000 or int(year) > 2100:
        raise ValueError("Año inválido.")

    liceo = _drive_folder_label(school_name, fallback="Liceo")
    curso = _drive_folder_label(course_name, fallback="Curso")
    doc_type = _drive_folder_label(document_type_name, fallback="Documento")
    ext = (file_extension or "docx").lower().lstrip(".")
    if ext not in {"docx", "pdf", "doc"}:
        ext = "docx"
    filename = _safe_filename(f"{rut_num}_{doc_type}.{ext}")

    try:
        liceo_id = _ensure_folder(config, root_id, liceo)
        year_id = _ensure_folder(config, liceo_id, year_label)
        course_id = _ensure_folder(config, year_id, curso)
        student_folder_id = _ensure_folder(config, course_id, rut_num)

        service = _service_for_config(config)
        try:
            from googleapiclient.http import MediaIoBaseUpload
        except ImportError as exc:
            raise ValueError("googleapiclient no está instalado.") from exc

        mime = mime_type or (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if ext == "docx"
            else "application/pdf"
            if ext == "pdf"
            else "application/octet-stream"
        )
        resumable = len(data) >= 5 * 1024 * 1024
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime, resumable=resumable)

        existing_id = _find_child_file(config, student_folder_id, filename)
        if existing_id:
            updated = (
                service.files()
                .update(
                    fileId=existing_id,
                    media_body=media,
                    fields="id,name,mimeType,size,webViewLink",
                    supportsAllDrives=True,
                )
                .execute()
            )
            file_meta = updated
            replaced = True
        else:
            body = {"name": filename, "parents": [student_folder_id]}
            file_meta = (
                service.files()
                .create(
                    body=body,
                    media_body=media,
                    fields="id,name,mimeType,size,webViewLink",
                    supportsAllDrives=True,
                )
                .execute()
            )
            replaced = False
    except Exception as exc:
        raise ValueError(_drive_api_error_message(exc)) from exc

    logical = f"{liceo}/{year_label}/{curso}/{rut_num}/{filename}"
    return {
        "ok": True,
        "file_id": file_meta.get("id"),
        "filename": file_meta.get("name") or filename,
        "mime_type": file_meta.get("mimeType") or mime,
        "size_bytes": int(file_meta.get("size") or len(data)),
        "web_view_link": file_meta.get("webViewLink"),
        "drive_path": logical,
        "replaced": replaced,
        "customer_id": int(customer_id),
        "school_name": liceo,
        "year": int(year),
        "course_name": curso,
        "student_rut_numeric": rut_num,
        "document_type_name": doc_type,
        "drive_config_source": config.source,
    }


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
    """Sube un archivo a Drive del customer: {root}/{agent_name}/[parent…]/file."""
    from app.backend.utils.school_drive_config import load_customer_drive_config

    if not data:
        raise ValueError("El archivo está vacío.")
    if int(customer_id) < 1:
        raise ValueError("customer_id inválido.")

    config = load_customer_drive_config(db, int(customer_id))
    root_id = config.root_folder_id.strip()
    agent_label = (agent_name or "").strip() or f"agent-{customer_id}"

    try:
        # La raíz ya es del customer: no anidar otro nivel customer_id.
        agent_folder_id = _ensure_folder(config, root_id, agent_label)

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

    logical = f"{agent_label}/{'/'.join(parts[:-1] + [name])}".replace("//", "/")
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
