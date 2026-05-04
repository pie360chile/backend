from typing import Optional

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, TeachingList, StoreTeaching, UpdateTeaching
from app.backend.classes.teaching_class import TeachingClass, _normalize_school_id
from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.inspection_api_client import InspectionApiClient
from app.backend.classes.school_class import SchoolClass

teachings = APIRouter(
    prefix="/teachings",
    tags=["Teachings"]
)


def _resolve_session_school_id(session_user, db: Session) -> Optional[int]:
    """
    Colegio efectivo de la sesión: school_id del usuario/JWT, o si hay customer_id
    y no hay school_id, el primer colegio activo de ese cliente (mismo criterio que /courses).
    """
    customer_id = session_user.customer_id if session_user else None
    school_id = session_user.school_id if session_user else None
    if customer_id and not school_id:
        schools_list = SchoolClass(db).get_all(page=0, customer_id=customer_id)
        if isinstance(schools_list, list) and len(schools_list) > 0:
            school_id = schools_list[0].get("id")
    return _normalize_school_id(school_id)


@teachings.post("/")
def index(teaching: TeachingList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Listado acotado al colegio de la sesión (JWT + resolución por customer_id si aplica).
    school_id = _resolve_session_school_id(session_user, db)

    # Si no hay school_id, devolver array vacío
    if school_id is None:
        message = "Complete teachings list retrieved successfully" if teaching.page is None else "Teachings retrieved successfully"
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": message,
                "data": [] if teaching.page is None else {
                    "total_items": 0,
                    "total_pages": 0,
                    "current_page": teaching.page if teaching.page else 1,
                    "items_per_page": teaching.per_page,
                    "data": []
                }
            }
        )
    
    page_value = 0 if teaching.page is None else teaching.page
    result = TeachingClass(db).get_all(page=page_value, items_per_page=teaching.per_page, teaching_name=teaching.teaching_name, school_id=school_id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error"),
                "data": None
            }
        )

    message = "Complete teachings list retrieved successfully" if teaching.page is None else "Teachings retrieved successfully"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@teachings.get("/list")
def get_all_list(school_id: int = None, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Listado del colegio de la sesión (normalizado). Query ?school_id solo si coincide (compat. frontend).
    session_sid = _resolve_session_school_id(session_user, db)
    requested = _normalize_school_id(school_id)
    if requested is not None and session_sid is not None and requested != session_sid:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status": 403,
                "message": "No autorizado para listar enseñanzas de otro colegio",
                "data": [],
            },
        )
    school_id = session_sid

    # Si no hay school_id, devolver array vacío
    if school_id is None:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Teachings list retrieved successfully",
                "data": []
            }
        )
    
    result = TeachingClass(db).get_all_list(school_id=school_id)

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
            "message": "Teachings list retrieved successfully",
            "data": result
        }
    )


@teachings.post("/import_from_inspection")
def import_from_inspection(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    school_id = _resolve_session_school_id(session_user, db)
    if school_id is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": 400,
                "message": (
                    "No se pudo determinar el colegio (school_id). "
                    "Asocia un colegio al usuario, inicia sesión con un token que incluya school_id, "
                    "o asegúrate de tener al menos un colegio activo para tu cliente (customer_id)."
                ),
                "data": None,
            },
        )

    client = InspectionApiClient()
    if not client.is_configured():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": 503,
                "message": "Inspection API not configured (INSPECTION_API_USERNAME / INSPECTION_API_PASSWORD)",
                "data": None,
            },
        )

    # GET https://…/api/listado/colegios → filtrar por id == school_id → tiposEnsenanzas
    remote = client.fetch_teachings_for_active_school(school_id)
    if not remote.get("ok"):
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "No se encontró el colegio" in (remote.get("message") or "")
            else status.HTTP_502_BAD_GATEWAY
        )
        return JSONResponse(
            status_code=status_code,
            content={
                "status": int(status_code),
                "message": remote.get("message") or "Error al obtener enseñanzas desde Inspection",
                "data": remote,
            },
        )

    result = TeachingClass(db).import_from_inspection(school_id, remote)
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error al importar enseñanzas"),
                "data": None,
            },
        )

    imported = result.get("imported", 0)
    skipped = result.get("skipped", 0)
    msg = f"Importación finalizada: {imported} nuevas, {skipped} omitidas (duplicadas o sin datos)."
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": msg,
            "data": result,
        },
    )


@teachings.post("/store")
def store(teaching: StoreTeaching, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    teaching_inputs = teaching.dict()
    school_id = _resolve_session_school_id(session_user, db)
    teaching_inputs['school_id'] = school_id
    
    result = TeachingClass(db).store(teaching_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating teaching"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Teaching created successfully",
            "data": result
        }
    )

@teachings.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = TeachingClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Teaching not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Teaching retrieved successfully",
            "data": result
        }
    )

@teachings.put("/update/{id}")
def update(id: int, teaching: UpdateTeaching, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    teaching_inputs = teaching.dict(exclude_unset=True)
    school_id = _resolve_session_school_id(session_user, db)
    teaching_inputs['school_id'] = school_id
    
    result = TeachingClass(db).update(id, teaching_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating teaching"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Teaching updated successfully",
            "data": result
        }
    )

@teachings.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = TeachingClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Teaching not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Teaching deleted successfully",
            "data": result
        }
    )