"""KPI: avance de documentación transversal (document_type_id = 1) por curso y por estudiante."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.kpi_documentation_progress_class import KpiDocumentationProgressClass
from app.backend.classes.professional_class import session_professional_scope_id
from app.backend.db.database import get_db
from app.backend.schemas import UserLogin

kpi_documentation_progress = APIRouter(
    prefix="/kpi/documentation-progress",
    tags=["KPI documentation progress"],
)


def _scope_allows_kpi(scope: Optional[int]) -> bool:
    """Solo coordinador/admin (sin restricción a un profesional)."""
    return scope is None


@kpi_documentation_progress.get("/by-course")
def kpi_doc_progress_by_course(
    period_year: int = Query(..., ge=2000, le=2100, description="Año escolar (period_year)"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    scope = session_professional_scope_id(db, session_user)
    if not _scope_allows_kpi(scope):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": []},
        )
    school_id = getattr(session_user, "school_id", None)
    if school_id is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": 400,
                "message": "school_id requerido",
                "data": [],
            },
        )

    svc = KpiDocumentationProgressClass(db)
    result = svc.by_course(school_id=int(school_id), period_year=period_year)
    if result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error"),
                "data": result.get("data"),
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "OK", "data": result.get("data")},
    )


@kpi_documentation_progress.get("/by-course/{course_id}/students")
def kpi_doc_progress_students(
    course_id: int,
    period_year: int = Query(..., ge=2000, le=2100),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    scope = session_professional_scope_id(db, session_user)
    if not _scope_allows_kpi(scope):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": None},
        )
    school_id = getattr(session_user, "school_id", None)
    if school_id is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": 400,
                "message": "school_id requerido",
                "data": None,
            },
        )

    svc = KpiDocumentationProgressClass(db)
    result = svc.students_detail(
        school_id=int(school_id),
        course_id=course_id,
        period_year=period_year,
    )
    if result.get("status") == "error":
        code = (
            status.HTTP_404_NOT_FOUND
            if "no encontrado" in str(result.get("message", "")).lower()
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        return JSONResponse(
            status_code=code,
            content={
                "status": 404 if code == 404 else 500,
                "message": result.get("message", "Error"),
                "data": result.get("data"),
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "OK", "data": result.get("data")},
    )
