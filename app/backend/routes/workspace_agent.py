"""Rutas Drive para el panel de Agentes (legado Workspace chat eliminado)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.workspace_agent_class import WorkspaceAgentClass
from app.backend.core.responses import api_error, api_response
from app.backend.db.database import get_db
from app.backend.schemas import UserLogin

workspace_agent = APIRouter(
    prefix="/workspace-agent",
    tags=["WorkspaceAgent"],
)


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
    from app.backend.utils.school_drive_config import (
        GOOGLE_DRIVE_DISABLED_MESSAGE,
        GOOGLE_DRIVE_ENABLED,
    )

    if not GOOGLE_DRIVE_ENABLED:
        return api_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=GOOGLE_DRIVE_DISABLED_MESSAGE,
        )
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
    from app.backend.utils.school_drive_config import (
        GOOGLE_DRIVE_DISABLED_MESSAGE,
        GOOGLE_DRIVE_ENABLED,
    )

    if not GOOGLE_DRIVE_ENABLED:
        return api_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=GOOGLE_DRIVE_DISABLED_MESSAGE,
        )
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