from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.learning_objective_class import LearningObjectiveClass
from app.backend.db.database import get_db
from app.backend.db.models import RolModel, UserModel
from app.backend.schemas import (
    StoreLearningObjectiveAdmin,
    UpdateLearningObjectiveAdmin,
    UserLogin,
)

learning_objectives = APIRouter(
    prefix="/learning_objectives",
    tags=["Learning Objectives"],
)


def _is_school_administrator(session_user: UserModel, db: Session) -> bool:
    """Administrador de establecimiento (rol 2 o nombre sin superadmin)."""
    if session_user.rol_id is None:
        return False
    rid = int(session_user.rol_id)
    if rid == 2:
        return True
    rol = db.query(RolModel).filter(RolModel.id == session_user.rol_id).first()
    if not rol or not rol.rol:
        return False
    n = str(rol.rol).lower()
    if "superadmin" in n or ("super" in n and "administrador" in n):
        return False
    return "administrador" in n and "super" not in n


def _require_school_administrator(session_user: UserModel, db: Session) -> None:
    if not _is_school_administrator(session_user, db):
        raise HTTPException(status_code=403, detail="No autorizado")


@learning_objectives.get("/education_levels")
def list_education_levels(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        result = LearningObjectiveClass(db).list_education_levels()
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error"), "data": []},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": result.get("data", [])},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": []},
        )


@learning_objectives.get("")
def list_learning_objectives(
    subject_name_es: str = Query(..., description="Nombre asignatura catálogo (ej. Artes visuales)"),
    education_level_id: int = Query(..., description="ID nivel educativo"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        result = LearningObjectiveClass(db).list_by_subject_and_level(
            subject_name_es, education_level_id
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error"),
                    "data": [],
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "OK"),
                "data": result.get("data", []),
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": []},
        )


@learning_objectives.get("/admin/{objective_id}")
def admin_get_learning_objective(
    objective_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_school_administrator(session_user, db)
    try:
        result = LearningObjectiveClass(db).admin_get(objective_id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": result.get("data")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@learning_objectives.post("/admin/store")
def admin_store_learning_objective(
    body: StoreLearningObjectiveAdmin,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_school_administrator(session_user, db)
    try:
        data = body.model_dump() if hasattr(body, "model_dump") else body.dict()
        result = LearningObjectiveClass(db).admin_store(data)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": 400, "message": result.get("message"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "Creado"),
                "data": result.get("data"),
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@learning_objectives.put("/admin/{objective_id}")
def admin_update_learning_objective(
    objective_id: int,
    body: UpdateLearningObjectiveAdmin,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_school_administrator(session_user, db)
    try:
        data = body.model_dump(exclude_unset=True) if hasattr(body, "model_dump") else body.dict(
            exclude_unset=True
        )
        result = LearningObjectiveClass(db).admin_update(objective_id, data)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": 400, "message": result.get("message"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Actualizado"),
                "data": result.get("data"),
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@learning_objectives.delete("/admin/{objective_id}")
def admin_delete_learning_objective(
    objective_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_school_administrator(session_user, db)
    try:
        result = LearningObjectiveClass(db).admin_delete(objective_id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Eliminado"), "data": None},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )
