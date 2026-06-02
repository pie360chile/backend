from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.learning_objective_class import LearningObjectiveClass
from app.backend.db.database import get_db
from app.backend.schemas import UserLogin

learning_objectives = APIRouter(
    prefix="/learning_objectives",
    tags=["Learning Objectives"],
)


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
