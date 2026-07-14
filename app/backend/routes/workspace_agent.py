from __future__ import annotations

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile, status, Depends
from sqlalchemy.orm import Session

from app.backend.classes.workspace_agent_class import WorkspaceAgentClass
from app.backend.core.config import settings
from app.backend.core.responses import api_error, api_response
from app.backend.db.database import get_db
from app.backend.schemas.workspace_agent import WorkspaceChatRequest
from app.backend.utils.agent_upload_token import verify_upload_token
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin

workspace_agent = APIRouter(
    prefix="/workspace-agent",
    tags=["WorkspaceAgent"],
)


def _require_mcp_secret(
    authorization: str | None = None,
    x_mcp_secret: str | None = None,
) -> None:
    if not settings.mcp_secret:
        return
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_mcp_secret:
        token = x_mcp_secret.strip()
    if token != settings.mcp_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Secret inválido")


@workspace_agent.post("/chat")
def trigger_workspace_agent_chat(
    body: WorkspaceChatRequest,
    db: Session = Depends(get_db),
):
    result = WorkspaceAgentClass(db).trigger_chat(body.input)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_502_BAD_GATEWAY),
            message=result.get("message", "Error"),
            data=result.get("data"),
        )
    return api_response(
        status_code=status.HTTP_200_OK,
        message=result.get("message", "OK"),
        data=result.get("data"),
    )


@workspace_agent.get("/agents")
def list_workspace_agents():
    result = WorkspaceAgentClass().list_agents()
    return api_response(data=result.get("data", []))


@workspace_agent.get("/agents/{agent_id}/files")
def list_workspace_agent_files(agent_id: str):
    result = WorkspaceAgentClass().list_files(agent_id)
    return api_response(data=result.get("data"))


@workspace_agent.post("/files/upload")
async def upload_workspace_agent_file(
    file: UploadFile = File(...),
    filename: str = Form(""),
    agent_id: str = Form(""),
    token: str = Query(""),
    authorization: str | None = Header(default=None),
    x_mcp_secret: str | None = Header(default=None),
):
    """Subida multipart de .docx. Auth: Bearer MCP_SECRET o ?token= (firmado por prepare_docx_upload)."""
    resolved_agent_id = agent_id or None
    resolved_filename = (filename or file.filename or "").strip()

    if token:
        try:
            claims = verify_upload_token(token)
        except ValueError as exc:
            return api_error(status_code=status.HTTP_401_UNAUTHORIZED, message=str(exc))
        resolved_agent_id = claims["agent_id"]
        if not resolved_filename:
            resolved_filename = claims["filename"]
        elif _safe_upload_name(resolved_filename) != claims["filename"]:
            return api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="filename no coincide con el token de subida.",
            )
    else:
        try:
            _require_mcp_secret(authorization, x_mcp_secret)
        except HTTPException as exc:
            return api_error(status_code=exc.status_code, message=str(exc.detail))

    data = await file.read()
    result = WorkspaceAgentClass().upload_file(resolved_filename, data, resolved_agent_id)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


def _safe_upload_name(value: str) -> str:
    from app.backend.utils.agent_workspace_storage import _safe_segment

    return _safe_segment(value.strip())


def _resolve_school_id(session_user: UserLogin, school_id_form: str) -> int:
    raw = (school_id_form or "").strip()
    if raw:
        try:
            return int(raw)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="school_id inválido.",
            ) from exc
    sid = getattr(session_user, "school_id", None)
    if sid is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selecciona un colegio en PIE360 antes de subir archivos.",
        )
    return int(sid)


def _resolve_period_year(session_user: UserLogin, year_form: str) -> int:
    """Año escolar activo: form explícito → JWT period_year → año calendario."""
    raw = (year_form or "").strip()
    if raw:
        try:
            y = int(raw)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="year inválido.",
            ) from exc
        if y < 2000 or y > 2100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="year inválido.",
            )
        return y
    py = getattr(session_user, "period_year", None)
    if py is not None:
        try:
            return int(py)
        except (TypeError, ValueError):
            pass
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).year


@workspace_agent.post("/drive/upload")
async def upload_to_google_drive(
    file: UploadFile = File(...),
    school_id: str = Form(""),
    year: str = Form(""),
    flow: str = Form("entry"),
    document_id: str = Form(...),
    student_id: str = Form(...),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Sube a Drive: {school_id}/{year}/{entry|exit}/{document_id}/{student_id}/."""
    sid = _resolve_school_id(session_user, school_id)
    try:
        doc_id = int(document_id)
        stu_id = int(student_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="document_id o student_id inválidos.",
        ) from exc

    year_val = _resolve_period_year(session_user, year)

    data = await file.read()
    result = WorkspaceAgentClass(db).upload_to_drive(
        school_id=sid,
        year=year_val,
        flow=(flow or "entry").strip().lower(),
        document_id=doc_id,
        student_id=stu_id,
        filename=file.filename or "archivo",
        data=data,
        mime_type=file.content_type,
    )
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


@workspace_agent.get("/drive/files")
def list_google_drive_files(
    document_id: int = Query(...),
    student_id: int = Query(...),
    flow: str = Query("entry"),
    year: int | None = Query(None),
    school_id: int | None = Query(None),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    sid = int(school_id) if school_id is not None else _resolve_school_id(session_user, "")
    resolved_year = int(year) if year is not None else _resolve_period_year(session_user, "")
    result = WorkspaceAgentClass(db).list_drive_files(
        school_id=sid,
        year=resolved_year,
        flow=(flow or "entry").strip().lower(),
        document_id=document_id,
        student_id=student_id,
    )
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(data=result.get("data"))
