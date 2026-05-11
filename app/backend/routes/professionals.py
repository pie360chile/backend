from typing import Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import ProfessionalList, StoreProfessional, UpdateProfessional, UserLogin
from app.backend.classes.professional_class import (
    ProfessionalClass,
    session_restricted_user_id,
)
from app.backend.classes.school_class import SchoolClass
from app.backend.auth.auth_user import get_current_active_user
from app.backend.utils.users_rol_period import resolve_period_year_for_session


def _session_school_id_with_fallback(db: Session, session_user) -> Optional[int]:
    """Colegio de la sesión o, si falta, primer colegio del cliente (igual que POST /professionals/)."""
    customer_id = getattr(session_user, "customer_id", None) if session_user else None
    school_id = getattr(session_user, "school_id", None) if session_user else None
    if school_id is None and customer_id:
        schools_list = SchoolClass(db).get_all(page=0, customer_id=customer_id)
        if isinstance(schools_list, list) and len(schools_list) > 0:
            sid = schools_list[0].get("id")
            school_id = int(sid) if sid is not None else None
    return school_id


def _school_id_from_request_or_session(db: Session, session_user, requested_school_id: Optional[int] = None) -> Optional[int]:
    if requested_school_id is not None:
        try:
            sid = int(requested_school_id)
            if sid > 0:
                return sid
        except (TypeError, ValueError):
            pass
    return _session_school_id_with_fallback(db, session_user)


def _ensure_professional_self_only(db, session_user, target_user_id: int, explicit_period_year=None):
    """Si no es rol institucional permitido, solo puede acceder a su propio ``users.id``."""
    scope = session_restricted_user_id(db, session_user, explicit_period_year)
    if scope is None:
        return
    if scope < 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene un registro de profesional asociado.",
        )
    if scope > 0 and target_user_id != scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede ver ni modificar datos de otros profesionales.",
        )

professionals = APIRouter(
    prefix="/professionals",
    tags=["Professionals"]
)

@professionals.post("/")
def index(professional_list: ProfessionalList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if professional_list.page is None else professional_list.page
    only_uid = session_restricted_user_id(db, session_user, professional_list.period_year)

    school_id = _school_id_from_request_or_session(db, session_user, professional_list.school_id)

    result = ProfessionalClass(db).get_all(
        page=page_value,
        items_per_page=professional_list.per_page,
        identification_number=professional_list.identification_number,
        names=professional_list.names,
        school_id=school_id,
        period_year=professional_list.period_year,
        only_professional_id=only_uid,
        session_rol_id=None,
    )
        
    message = "Complete professionals list retrieved successfully" if professional_list.page is None else "Professionals retrieved successfully"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@professionals.post("/list")
def list_professionals(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    body: Optional[dict] = Body(default=None),
):
    body = body or {}
    requested_school_id = body.get("school_id")
    school_id = _school_id_from_request_or_session(db, session_user, requested_school_id)
    py = resolve_period_year_for_session(session_user, body.get("period_year"))
    only_uid = session_restricted_user_id(db, session_user, py)
    result = ProfessionalClass(db).get_all(
        page=0,
        school_id=school_id,
        period_year=py,
        only_professional_id=only_uid,
        session_rol_id=None,
    )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Professionals list retrieved successfully",
            "data": result
        }
    )

@professionals.get("/list")
def get_all_list(
    period_year: Optional[int] = Query(None, description="Filtrar por año (ej. 2026)"),
    school_id: Optional[int] = Query(None, description="Filtrar por colegio"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    school_id = _school_id_from_request_or_session(db, session_user, school_id)

    if school_id is None:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Professionals list retrieved successfully",
                "data": [],
            },
        )

    py = resolve_period_year_for_session(session_user, period_year)
    only_uid = session_restricted_user_id(db, session_user, py)
    result = ProfessionalClass(db).get_all(
        page=0,
        school_id=school_id,
        period_year=py,
        only_professional_id=only_uid,
        session_rol_id=None,
    )

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error"),
                "data": None
            }
        )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Professionals list retrieved successfully",
            "data": result
        }
    )

@professionals.post("/totals")
def totals(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    body: Optional[dict] = Body(default=None),
):
    body = body or {}
    customer_id = session_user.customer_id if session_user else None
    school_id = _school_id_from_request_or_session(db, session_user, body.get("school_id"))
    rol_id = session_user.rol_id if session_user else None
    py = resolve_period_year_for_session(session_user, body.get("period_year"))
    only_uid = session_restricted_user_id(db, session_user, py)
    result = ProfessionalClass(db).get_totals(
        customer_id=customer_id,
        school_id=school_id,
        rol_id=rol_id,
        only_professional_id=only_uid,
        period_year=py,
    )

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error getting totals"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Professionals totals retrieved successfully",
            "data": result
        }
    )

@professionals.post("/store")
def store(professional: StoreProfessional, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    if session_restricted_user_id(db, session_user, professional.period_year) is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo coordinadores o administradores pueden crear profesionales.",
        )
    professional_inputs = professional.dict()

    school_id = _school_id_from_request_or_session(db, session_user, professional.school_id)

    result = ProfessionalClass(db).store(professional_inputs, school_id=school_id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating professional"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Professional and user created successfully",
            "data": result
        }
    )

@professionals.get("/coordinators/{school_id}")
def get_coordinators_by_school(
    school_id: int,
    period_year: Optional[int] = Query(None, description="Año período escolar"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista de coordinadores del colegio: filtra por school_id y rol 'Coordinador' (el rol_id es distinto por escuela)."""
    py = resolve_period_year_for_session(session_user, period_year)
    result = ProfessionalClass(db).get_coordinators_by_school(school_id, period_year=py)
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error al listar coordinadores"),
                "data": [],
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Coordinadores del colegio",
            "data": result if isinstance(result, list) else [],
        },
    )


@professionals.get("/edit/{id}")
def edit(
    id: int,
    period_year: Optional[int] = Query(None, description="Año período escolar (users_rols)"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    py = resolve_period_year_for_session(session_user, period_year)
    _ensure_professional_self_only(db, session_user, id, py)
    sid = _school_id_from_request_or_session(db, session_user, None)
    result = ProfessionalClass(db).get(id, school_id=sid, period_year=py)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Professional not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Professional retrieved successfully",
            "data": result
        }
    )

@professionals.delete("/delete/{id}")
def delete(
    id: int,
    period_year: Optional[int] = Query(None, description="Año período escolar (users_rols)"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    py = resolve_period_year_for_session(session_user, period_year)
    _ensure_professional_self_only(db, session_user, id, py)
    sid = _school_id_from_request_or_session(db, session_user, None)
    result = ProfessionalClass(db).delete(id, school_id=sid, period_year=py)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Professional not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Professional deleted successfully",
            "data": result
        }
    )

@professionals.put("/update/{id}")
def update(
    id: int,
    professional: UpdateProfessional,
    period_year: Optional[int] = Query(None, description="Año período escolar (users_rols)"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    py = resolve_period_year_for_session(
        session_user,
        period_year if period_year is not None else professional.period_year,
    )
    _ensure_professional_self_only(db, session_user, id, py)
    professional_inputs = professional.dict(exclude_unset=True)

    # Agregar school_id de la sesión si no viene en el input
    if 'school_id' not in professional_inputs:
        professional_inputs['school_id'] = _school_id_from_request_or_session(db, session_user, None)

    sid = _school_id_from_request_or_session(db, session_user, professional_inputs.get("school_id"))
    result = ProfessionalClass(db).update(id, professional_inputs, school_id=sid, period_year=py)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating professional"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Professional updated successfully",
            "data": result
        }
    )
