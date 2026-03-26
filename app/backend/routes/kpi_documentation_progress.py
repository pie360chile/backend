"""KPI: avance de documentación transversal (document_type_id = 1) por curso y por estudiante."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.kpi_documentation_progress_class import KpiDocumentationProgressClass
from app.backend.classes.professional_class import session_professional_scope_id
from app.backend.db.database import get_db
from app.backend.db.models import SchoolModel
from app.backend.schemas import UserLogin

kpi_documentation_progress = APIRouter(
    prefix="/kpi/documentation-progress",
    tags=["KPI documentation progress"],
)


def _scope_allows_kpi(scope: Optional[int]) -> bool:
    """Solo coordinador/admin (sin restricción a un profesional)."""
    return scope is None


def _resolve_doc_kpi_school_ids(db: Session, session_user: UserLogin) -> List[int]:
    """Administrador cliente: todos los colegios del customer. Super (rol 1 sin customer): todos. Resto: sesión."""
    rol_id = getattr(session_user, "rol_id", None)
    customer_id = getattr(session_user, "customer_id", None)
    school_id = getattr(session_user, "school_id", None)

    if rol_id is not None and int(rol_id) in (1, 2) and customer_id is not None:
        rows = (
            db.query(SchoolModel.id)
            .filter(SchoolModel.customer_id == int(customer_id))
            .order_by(SchoolModel.school_name.asc())
            .all()
        )
        return [int(r[0]) for r in rows]

    if rol_id is not None and int(rol_id) == 1 and customer_id is None:
        rows = db.query(SchoolModel.id).order_by(SchoolModel.school_name.asc()).all()
        return [int(r[0]) for r in rows]

    if school_id is not None:
        return [int(school_id)]
    return []


def _school_allowed_for_doc_kpi(
    db: Session, session_user: UserLogin, school_id: int
) -> bool:
    sid = int(school_id)
    rol_id = getattr(session_user, "rol_id", None)
    customer_id = getattr(session_user, "customer_id", None)
    session_school = getattr(session_user, "school_id", None)

    if rol_id is not None and int(rol_id) in (1, 2) and customer_id is not None:
        sch = db.query(SchoolModel).filter(SchoolModel.id == sid).first()
        return sch is not None and int(sch.customer_id) == int(customer_id)

    if rol_id is not None and int(rol_id) == 1 and customer_id is None:
        return db.query(SchoolModel).filter(SchoolModel.id == sid).first() is not None

    if session_school is not None:
        return int(session_school) == sid
    return False


@kpi_documentation_progress.get("/by-school")
def kpi_doc_progress_by_school(
    period_year: int = Query(..., ge=2000, le=2100, description="Año escolar (period_year)"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Resumen por establecimiento (administración: varios colegios del customer)."""
    scope = session_professional_scope_id(db, session_user)
    if not _scope_allows_kpi(scope):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": []},
        )
    school_ids = _resolve_doc_kpi_school_ids(db, session_user)
    if not school_ids:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": 400,
                "message": "No hay establecimientos asociados al usuario",
                "data": [],
            },
        )
    svc = KpiDocumentationProgressClass(db)
    result = svc.by_school(school_ids=school_ids, period_year=period_year)
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


@kpi_documentation_progress.get("/by-course")
def kpi_doc_progress_by_course(
    period_year: int = Query(..., ge=2000, le=2100, description="Año escolar (period_year)"),
    school_id: Optional[int] = Query(
        None,
        ge=1,
        description="Establecimiento (admin puede filtrar; si no, se usa school_id de sesión)",
    ),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    scope = session_professional_scope_id(db, session_user)
    if not _scope_allows_kpi(scope):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": []},
        )
    effective = school_id if school_id is not None else getattr(session_user, "school_id", None)
    if effective is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": 400,
                "message": "school_id requerido",
                "data": [],
            },
        )
    if not _school_allowed_for_doc_kpi(db, session_user, int(effective)):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status": 403,
                "message": "Sin acceso a este establecimiento",
                "data": [],
            },
        )

    svc = KpiDocumentationProgressClass(db)
    result = svc.by_course(school_id=int(effective), period_year=period_year)
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
    school_id: Optional[int] = Query(
        None,
        ge=1,
        description="Establecimiento (admin con varios colegios; si no, se usa school_id de sesión)",
    ),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    scope = session_professional_scope_id(db, session_user)
    if not _scope_allows_kpi(scope):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": None},
        )
    effective = school_id if school_id is not None else getattr(session_user, "school_id", None)
    if effective is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": 400,
                "message": "school_id requerido",
                "data": None,
            },
        )
    if not _school_allowed_for_doc_kpi(db, session_user, int(effective)):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status": 403,
                "message": "Sin acceso a este establecimiento",
                "data": None,
            },
        )

    svc = KpiDocumentationProgressClass(db)
    result = svc.students_detail(
        school_id=int(effective),
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
