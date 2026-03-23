"""KPI: documentos asignados vs cargados (por curso y detalle por profesional)."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.kpi_document_assignments_class import KpiDocumentAssignmentsClass
from app.backend.classes.professional_class import session_professional_scope_id
from app.backend.db.database import get_db
from app.backend.schemas import UserLogin

kpi_document_assignments = APIRouter(
    prefix="/kpi/document-assignments",
    tags=["KPI document assignments"],
)


@kpi_document_assignments.get("/by-course")
def kpi_by_course(
    year: int = Query(..., ge=2000, le=2100, description="Año calendario del mes a consultar"),
    month: int = Query(..., ge=1, le=12, description="Mes calendario (1-12) sobre added_date"),
    period_year: Optional[int] = Query(
        None,
        ge=2000,
        le=2100,
        description="Opcional: filtrar por period_year de la asignación (el front del KPI no lo envía)",
    ),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    scope = session_professional_scope_id(db, session_user)
    if scope == -1:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": []},
        )
    prof_filter = scope if scope and scope > 0 else None
    svc = KpiDocumentAssignmentsClass(db)
    result = svc.by_course(
        period_year=period_year,
        year=year,
        month=month,
        professional_id_filter=prof_filter,
    )
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


@kpi_document_assignments.get("/by-course/{course_id}/professionals")
def kpi_by_professional(
    course_id: int,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    period_year: Optional[int] = Query(None, ge=2000, le=2100),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    scope = session_professional_scope_id(db, session_user)
    if scope == -1:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": []},
        )
    prof_filter = scope if scope and scope > 0 else None
    svc = KpiDocumentAssignmentsClass(db)
    result = svc.by_professional(
        period_year=period_year,
        course_id=course_id,
        year=year,
        month=month,
        professional_id_filter=prof_filter,
    )
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


@kpi_document_assignments.get("/by-course/{course_id}/by-document")
def kpi_by_document(
    course_id: int,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    period_year: Optional[int] = Query(None, ge=2000, le=2100),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Por tipo de documento (catálogo): asignados y cargados (detalle del profesional)."""
    scope = session_professional_scope_id(db, session_user)
    if scope == -1:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": []},
        )
    prof_filter = scope if scope and scope > 0 else None
    svc = KpiDocumentAssignmentsClass(db)
    result = svc.by_document(
        period_year=period_year,
        course_id=course_id,
        year=year,
        month=month,
        professional_id_filter=prof_filter,
    )
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
