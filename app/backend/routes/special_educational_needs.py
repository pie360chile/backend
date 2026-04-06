from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import SpecialEducationalNeedList, StoreSpecialEducationalNeed, UpdateSpecialEducationalNeed
from app.backend.classes.special_educational_need_class import SpecialEducationalNeedClass
from app.backend.auth.auth_user import get_current_active_user
from app.backend.db.models import UserModel, RolModel

special_educational_needs = APIRouter(
    prefix="/special_educational_needs",
    tags=["Special Educational Needs"]
)


def _school_id_from_user(session_user: UserModel) -> Optional[int]:
    """Active school from user/token (same as select_school / login)."""
    sid = getattr(session_user, "school_id", None)
    if sid is None:
        return None
    try:
        i = int(sid)
        return i if i > 0 else None
    except (TypeError, ValueError):
        return None


def _can_manage_nee_catalog(session_user: UserModel, db: Session) -> bool:
    """
    Who may manage the NEE catalog (aligned with frontend `neeMenuAccess.ts`).
    Deny: rol_id 1 (superadmin); professor/professional role names without coordinator/evaluator.
    Allow: rol_id 2 (school admin); role name contains coordinator/evaluator; administrator without "super".
    """
    if session_user.rol_id is None:
        return False
    rid = int(session_user.rol_id)
    if rid == 1:
        return False
    if rid == 2:
        return True
    rol = db.query(RolModel).filter(RolModel.id == session_user.rol_id).first()
    if not rol or not rol.rol:
        return False
    n = str(rol.rol).lower()
    if "superadmin" in n or ("super" in n and "administrador" in n):
        return False
    if "coordinador" in n or "evaluador" in n:
        return True
    if "administrador" in n and "super" not in n:
        return True
    if "profesor" in n or "profesional" in n:
        return False
    return False


def _require_nee_catalog_access(session_user: UserModel, db: Session) -> None:
    if not _can_manage_nee_catalog(session_user, db):
        raise HTTPException(status_code=403, detail="No autorizado")


@special_educational_needs.post("/")
def index(need: SpecialEducationalNeedList, session_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_nee_catalog_access(session_user, db)
    sid = _school_id_from_user(session_user)
    if sid is None:
        raise HTTPException(status_code=400, detail="Se requiere colegio en la sesión (school_id)")
    page_value = 0 if need.page is None else need.page
    result = SpecialEducationalNeedClass(db).get_all(
        page=page_value,
        items_per_page=need.per_page,
        special_educational_needs=need.special_educational_needs,
        special_educational_need_type_id=need.special_educational_need_type_id,
        school_id=sid,
    )

    if isinstance(result, dict) and result.get("status") == "error":
        error_message = result.get("message", "Error")
        lower_message = error_message.lower() if isinstance(error_message, str) else ""

        if "no data" in lower_message or "no se encontraron datos" in lower_message:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": 200,
                    "message": error_message,
                    "data": []
                }
            )

        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": error_message,
                "data": None
            }
        )

    message = "Complete special educational needs list retrieved successfully" if need.page is None else "Special educational needs retrieved successfully"

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@special_educational_needs.post("/store")
def store(need: StoreSpecialEducationalNeed, session_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_nee_catalog_access(session_user, db)
    sid = _school_id_from_user(session_user)
    if sid is None:
        raise HTTPException(status_code=400, detail="Se requiere colegio en la sesión (school_id)")
    need_inputs = need.dict()
    need_inputs["school_id"] = sid
    result = SpecialEducationalNeedClass(db).store(need_inputs, school_id=sid)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating special educational need"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Special educational need created successfully",
            "data": result
        }
    )

@special_educational_needs.get("/edit/{id}")
def edit(id: int, session_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_nee_catalog_access(session_user, db)
    sid = _school_id_from_user(session_user)
    if sid is None:
        raise HTTPException(status_code=400, detail="Se requiere colegio en la sesión (school_id)")
    result = SpecialEducationalNeedClass(db).get(id, school_id=sid)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Special educational need not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Special educational need retrieved successfully",
            "data": result
        }
    )

@special_educational_needs.put("/update/{id}")
def update(id: int, need: UpdateSpecialEducationalNeed, session_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_nee_catalog_access(session_user, db)
    sid = _school_id_from_user(session_user)
    if sid is None:
        raise HTTPException(status_code=400, detail="Se requiere colegio en la sesión (school_id)")
    need_inputs = need.dict(exclude_unset=True)
    result = SpecialEducationalNeedClass(db).update(id, need_inputs, school_id=sid)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating special educational need"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Special educational need updated successfully",
            "data": result
        }
    )

@special_educational_needs.delete("/delete/{id}")
def delete(id: int, session_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_nee_catalog_access(session_user, db)
    sid = _school_id_from_user(session_user)
    if sid is None:
        raise HTTPException(status_code=400, detail="Se requiere colegio en la sesión (school_id)")
    result = SpecialEducationalNeedClass(db).delete(id, school_id=sid)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Special educational need not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Special educational need deleted successfully",
            "data": result
        }
    )

@special_educational_needs.get("/list")
def list_all(session_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Lectura para selects (profesor, etc.): solo autenticación; filtro por school_id de sesión.
    sid = _school_id_from_user(session_user)
    result = SpecialEducationalNeedClass(db).get_all(page=0, items_per_page=None, school_id=sid)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error retrieving special educational needs"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Special educational needs list retrieved successfully",
            "data": result
        }
    )
