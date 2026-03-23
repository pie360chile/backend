from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.app_alert_class import AppAlertClass
from app.backend.classes.professional_class import session_professional_scope_id
from app.backend.classes.professional_document_assignment_class import ProfessionalDocumentAssignmentClass
from app.backend.db.database import get_db
from app.backend.schemas import UserLogin

professional_document_assignments = APIRouter(
    prefix="/professional_document_assignments",
    tags=["Professional document assignments"],
)


@professional_document_assignments.get("/home-stats")
def professional_home_stats(
    period_year: Optional[int] = Query(
        None,
        ge=2000,
        le=2100,
        description="Año de período escolar (alineado a cookie); si se omite, cuenta todos los períodos en documentos",
    ),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Totales para el home del profesional: documentos, cursos PTC y estudiantes por curso."""
    scope = session_professional_scope_id(db, session_user)
    if scope is None:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"status": 403, "message": "No autorizado", "data": None},
        )
    if scope < 0:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "OK",
                "data": {
                    "assigned_documents": 0,
                    "loaded_documents": 0,
                    "courses_assigned": 0,
                    "students_in_courses": 0,
                },
            },
        )
    svc = ProfessionalDocumentAssignmentClass(db)
    result = svc.home_stats(professional_id=scope, period_year=period_year)
    if result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error"),
                "data": None,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "OK", "data": result.get("data")},
    )


@professional_document_assignments.get("/pending-count")
def pending_assignments_count(
    professional_id: int = Query(..., description="ID del profesional"),
    period_year: Optional[int] = Query(
        None,
        description="Año de período escolar; si se omite, cuenta todos los períodos",
    ),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Prioridad: si el profesional ya tiene filas en `alerts`, el contador es solo alertas no revisadas.
    Si aún no hay alertas (tabla vacía / sin migrar), se usa el conteo de asignaciones pendientes.
    """
    alert_svc = AppAlertClass(db)
    ar = alert_svc.count_unread(professional_id)
    use_alerts = ar.get("status") == "success" and alert_svc.has_any_alert_for_professional(
        professional_id
    )
    if use_alerts:
        cnt = int(ar.get("count", 0))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "OK",
                "data": {"count": cnt, "source": "alerts"},
            },
        )
    svc = ProfessionalDocumentAssignmentClass(db)
    result = svc.count_pending(
        professional_id=professional_id,
        period_year=period_year,
    )
    if result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error"),
                "data": {"count": 0},
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "OK",
            "data": {
                "count": int(result.get("count", 0)),
                "source": "assignments",
            },
        },
    )


class AssignmentSyncItem(BaseModel):
    document_type_id: int
    document_id: Optional[int] = None
    student_ids: List[int] = Field(default_factory=list)
    deadline_at: Optional[str] = None


class AssignmentSyncBody(BaseModel):
    course_id: int
    professional_id: int
    period_year: int
    items: List[AssignmentSyncItem] = Field(default_factory=list)


@professional_document_assignments.get("/")
def list_assignments(
    course_id: int = Query(...),
    professional_id: int = Query(...),
    period_year: int = Query(..., ge=2000, le=2100),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    svc = ProfessionalDocumentAssignmentClass(db)
    result = svc.get_grouped(
        period_year=period_year,
        course_id=course_id,
        professional_id=professional_id,
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
        content={
            "status": 200,
            "message": "OK",
            "data": result.get("data"),
        },
    )


@professional_document_assignments.post("/")
def sync_assignments(
    body: AssignmentSyncBody,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    svc = ProfessionalDocumentAssignmentClass(db)
    items_payload: List[Dict[str, Any]] = [
        {
            "document_type_id": it.document_type_id,
            "document_id": it.document_id,
            "student_ids": it.student_ids,
            "deadline_at": it.deadline_at,
        }
        for it in body.items
    ]
    result = svc.sync_replace(
        period_year=body.period_year,
        course_id=body.course_id,
        professional_id=body.professional_id,
        items=items_payload,
    )
    if result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error al guardar"),
                "data": None,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": result.get("message", "OK"), "data": None},
    )
