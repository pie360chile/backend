import json

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.agents_chat_class import AgentsChatClass
from app.backend.classes.agents_class import AgentsClass
from app.backend.classes.agents_llm_models_class import AgentsLlmModelsClass
from app.backend.classes.agents_rate_limit_class import (
    AgentsRateLimitClass,
    can_use_agents_chat,
)
from app.backend.core.responses import api_error, api_response
from app.backend.db.database import get_db
from app.backend.db.models import UserModel
from app.backend.schemas.agents import (
    AgentChatRequest,
    AgentCreateFolderRequest,
    AgentCreateRequest,
    AgentsSettingsUpdateRequest,
)

agents = APIRouter(
    prefix="/agents",
    tags=["Agents"],
)


def _resolve_customer_id(
    session_user: UserModel,
    requested: int | None = None,
) -> tuple[int | None, str | None]:
    """
    Agents are scoped per client (customer_id).
    Non-superadmin: always their session customer_id.
    Superadmin: optional requested customer_id, else session customer_id.
    """
    rol_id = int(getattr(session_user, "rol_id", 0) or 0)
    own = getattr(session_user, "customer_id", None)
    own_id = int(own) if own else None

    if rol_id == 1:
        if requested is not None and int(requested) > 0:
            return int(requested), None
        if own_id:
            return own_id, None
        return None, "Selecciona un cliente para gestionar sus agentes."

    if not own_id:
        return None, "No hay cliente asociado a la sesión."

    if requested is not None and int(requested) > 0 and int(requested) != own_id:
        return None, "No puedes gestionar agentes de otro cliente."

    return own_id, None


def _forbid_agents_access(session_user: UserModel, db: Session):
    if can_use_agents_chat(session_user, db):
        return None
    return api_error(
        status_code=status.HTTP_403_FORBIDDEN,
        message="No tienes permiso para usar Agents. Solo superadmin, coordinador o evaluador.",
    )


@agents.get("/documents/catalog")
def list_catalog_documents(
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    if int(getattr(session_user, "rol_id", 0) or 0) != 1:
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only the superadministrator can manage agent documents.",
        )
    result = AgentsClass(db).list_catalog_documents()
    return api_response(data=result.get("data", []))


@agents.get("/settings")
def get_agents_settings(
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    if int(getattr(session_user, "rol_id", 0) or 0) != 1:
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only the superadministrator can manage Agents settings.",
        )
    # Modelo y agente por defecto son globales para toda la web.
    data = AgentsLlmModelsClass(db).get_settings(customer_id=None)
    return api_response(data=data)


@agents.get("/reports")
def agents_usage_reports(
    customer_id: int | None = Query(None),
    day: str | None = Query(None, description="YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    if int(getattr(session_user, "rol_id", 0) or 0) != 1:
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only the superadministrator can view Agents reports.",
        )
    from datetime import date as date_cls

    from app.backend.classes.agents_usage_class import AgentsUsageClass

    parsed_day = None
    if day:
        try:
            parsed_day = date_cls.fromisoformat(day.strip())
        except ValueError:
            return api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Formato de día inválido. Usa YYYY-MM-DD.",
            )
    result = AgentsUsageClass(db).list_report(
        customer_id=customer_id,
        day=parsed_day,
        page=page,
        per_page=per_page,
    )
    return api_response(data=result.get("data"))


@agents.put("/settings")
def update_agents_settings(
    payload: AgentsSettingsUpdateRequest,
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    if int(getattr(session_user, "rol_id", 0) or 0) != 1:
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only the superadministrator can manage Agents settings.",
        )
    result = AgentsLlmModelsClass(db).update_settings(
        selected_model_code=payload.selected_model_code,
        selected_model_name=payload.selected_model_name,
        default_agent_id=payload.default_agent_id,
        clear_default_agent=payload.clear_default_agent,
        llm_api_key=payload.llm_api_key,
        clear_llm_api_key=payload.clear_llm_api_key,
        google_drive_root_folder_id=payload.google_drive_root_folder_id,
        google_service_account_json=payload.google_service_account_json,
        clear_google_drive=payload.clear_google_drive,
    )
    if result.get("status") == "error":
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=result.get("message") or "No se pudo guardar.",
        )
    data = AgentsLlmModelsClass(db).get_settings(customer_id=None)
    return api_response(message=result.get("message"), data=data)


@agents.post("/settings/sync-drive-folders")
def sync_agents_drive_folders(
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    """Crea en Drive {customer_id}/{agent_name}/ bajo la raíz de Agentes (si no existen)."""
    if int(getattr(session_user, "rol_id", 0) or 0) != 1:
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only the superadministrator can manage Agents settings.",
        )
    from app.backend.utils import google_drive_storage as drive_storage

    try:
        result = drive_storage.sync_customer_agent_folders(db)
    except Exception as exc:
        return api_error(
            status_code=status.HTTP_502_BAD_GATEWAY,
            message=f"Error al sincronizar carpetas en Google Drive: {exc}",
        )
    if not result.get("ok"):
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=result.get("message") or "No se pudo sincronizar Drive.",
            data=result,
        )
    return api_response(message=result.get("message"), data=result)


@agents.get("")
def list_agents(
    customer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    denied = _forbid_agents_access(session_user, db)
    if denied:
        return denied
    cid, err = _resolve_customer_id(session_user, customer_id)
    if err or not cid:
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=err or "customer_id is required",
        )
    result = AgentsClass(db).list_agents(cid)
    return api_response(data=result.get("data", []))


@agents.post("")
def create_agent(
    body: AgentCreateRequest,
    customer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    rol_id = getattr(session_user, "rol_id", None)
    if int(rol_id or 0) != 1:
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only the superadministrator can create agents.",
        )
    requested = body.customer_id if body.customer_id is not None else customer_id
    cid, err = _resolve_customer_id(session_user, requested)
    if err or not cid:
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=err or "customer_id is required",
        )
    result = AgentsClass(db).create_agent(cid, body.name, body.role_instructions)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message=result.get("message", "OK"),
        data=result.get("data"),
    )


@agents.get("/{agent_id}/document-templates")
def list_agent_document_templates(
    agent_id: str,
    customer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    if int(getattr(session_user, "rol_id", 0) or 0) != 1:
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only the superadministrator can manage agent documents.",
        )
    cid, err = _resolve_customer_id(session_user, customer_id)
    if err or not cid:
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=err or "customer_id is required",
        )
    result = AgentsClass(db).list_document_templates(agent_id, cid)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_404_NOT_FOUND),
            message=result.get("message", "Error"),
        )
    return api_response(data=result.get("data", []))


@agents.post("/{agent_id}/document-templates/{document_id}")
async def upload_agent_document_template(
    agent_id: str,
    document_id: int,
    file: UploadFile = File(...),
    document_name: str = Form(""),
    customer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    if int(getattr(session_user, "rol_id", 0) or 0) != 1:
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only the superadministrator can manage agent documents.",
        )
    cid, err = _resolve_customer_id(session_user, customer_id)
    if err or not cid:
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=err or "customer_id is required",
        )
    data = await file.read()
    result = AgentsClass(db).save_document_template(
        agent_id,
        cid,
        document_id,
        document_name,
        data,
        file.filename or "template.docx",
    )
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


@agents.post("/{agent_id}/chat")
def chat_agent(
    agent_id: str,
    body: AgentChatRequest,
    customer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    denied = _forbid_agents_access(session_user, db)
    if denied:
        return denied
    cid, err = _resolve_customer_id(session_user, customer_id)
    if err or not cid:
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=err or "customer_id is required",
        )
    history = [{"role": m.role, "content": m.content} for m in body.history]
    school_id = getattr(session_user, "school_id", None)
    user_id = getattr(session_user, "id", None)

    rate = AgentsRateLimitClass(db).check_and_register_chat(
        user_id=int(user_id) if user_id else None,
        customer_id=int(cid),
        school_id=int(school_id) if school_id else None,
    )
    if not rate.get("ok"):
        return api_error(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message=rate.get("message") or "Rate limit exceeded",
        )

    def event_stream():
        chat = AgentsChatClass(
            db,
            customer_id=cid,
            school_id=int(school_id) if school_id else None,
            user_id=int(user_id) if user_id else None,
        )
        for event in chat.stream_chat(
            agent_id,
            body.message,
            student_id=body.student_id,
            student_rut=body.student_rut,
            document_id=body.document_id,
            history=history,
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@agents.get("/{agent_id}/files")
def list_agent_files(
    agent_id: str,
    path: str = Query(""),
    customer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    denied = _forbid_agents_access(session_user, db)
    if denied:
        return denied
    cid, err = _resolve_customer_id(session_user, customer_id)
    if err or not cid:
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=err or "customer_id is required",
        )
    result = AgentsClass(db).list_files(agent_id, cid, path)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_404_NOT_FOUND),
            message=result.get("message", "Error"),
        )
    return api_response(data=result.get("data"))


@agents.post("/{agent_id}/files/folder")
def create_agent_folder(
    agent_id: str,
    body: AgentCreateFolderRequest,
    customer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    if int(getattr(session_user, "rol_id", 0) or 0) != 1:
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only the superadministrator can manage agent files.",
        )
    cid, err = _resolve_customer_id(session_user, customer_id)
    if err or not cid:
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=err or "customer_id is required",
        )
    result = AgentsClass(db).create_folder(agent_id, cid, body.name, body.parent_path)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


@agents.post("/{agent_id}/files/upload")
async def upload_agent_files(
    agent_id: str,
    files: list[UploadFile] = File(...),
    relative_paths: str = Form("[]"),
    customer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    if int(getattr(session_user, "rol_id", 0) or 0) != 1:
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only the superadministrator can manage agent files.",
        )
    cid, err = _resolve_customer_id(session_user, customer_id)
    if err or not cid:
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=err or "customer_id is required",
        )
    try:
        paths = json.loads(relative_paths)
    except json.JSONDecodeError:
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="relative_paths must be a JSON array.",
        )
    if not isinstance(paths, list):
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="relative_paths must be a JSON array.",
        )

    payload: list[tuple[str, bytes]] = []
    for index, upload in enumerate(files):
        data = await upload.read()
        rel = str(paths[index] if index < len(paths) else upload.filename or "file")
        payload.append((rel, data))

    result = AgentsClass(db).upload_files(agent_id, cid, payload)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


@agents.delete("/{agent_id}/files")
def delete_agent_file(
    agent_id: str,
    path: str = Query(..., min_length=1),
    customer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    if int(getattr(session_user, "rol_id", 0) or 0) != 1:
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only the superadministrator can manage agent files.",
        )
    cid, err = _resolve_customer_id(session_user, customer_id)
    if err or not cid:
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=err or "customer_id is required",
        )
    result = AgentsClass(db).delete_file(agent_id, cid, path)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"))


@agents.get("/{agent_id}")
def get_agent(
    agent_id: str,
    customer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    denied = _forbid_agents_access(session_user, db)
    if denied:
        return denied
    cid, err = _resolve_customer_id(session_user, customer_id)
    if err or not cid:
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=err or "customer_id is required",
        )
    result = AgentsClass(db).get_agent(agent_id, cid)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_404_NOT_FOUND),
            message=result.get("message", "Error"),
        )
    return api_response(data=result.get("data"))


@agents.put("/{agent_id}")
def update_agent(
    agent_id: str,
    body: AgentCreateRequest,
    customer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    rol_id = getattr(session_user, "rol_id", None)
    if int(rol_id or 0) != 1:
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only the superadministrator can edit agents.",
        )
    requested = body.customer_id if body.customer_id is not None else customer_id
    cid, err = _resolve_customer_id(session_user, requested)
    if err or not cid:
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=err or "customer_id is required",
        )
    result = AgentsClass(db).update_agent(agent_id, cid, body.name, body.role_instructions)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


@agents.delete("/{agent_id}")
def delete_agent(
    agent_id: str,
    customer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    rol_id = getattr(session_user, "rol_id", None)
    if int(rol_id or 0) != 1:
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only the superadministrator can delete agents.",
        )
    cid, err = _resolve_customer_id(session_user, customer_id)
    if err or not cid:
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=err or "customer_id is required",
        )
    result = AgentsClass(db).delete_agent(agent_id, cid)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_404_NOT_FOUND),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"))
