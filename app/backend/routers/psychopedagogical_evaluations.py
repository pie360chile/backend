"""Router: Document 27 – Psychopedagogical Evaluation Information."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import (
    UserLogin,
    StorePsychopedagogicalEvaluationInfo,
    UpdatePsychopedagogicalEvaluationInfo,
)
from app.backend.classes.psychopedagogical_evaluation_class import PsychopedagogicalEvaluationClass
from sqlalchemy.orm import Session
from typing import Optional

psychopedagogical_evaluations = APIRouter(
    prefix="/psychopedagogical_evaluations",
    tags=["Psychopedagogical Evaluation (Document 27)"],
)


@psychopedagogical_evaluations.get("/by_student/{student_id}")
def get_by_student_id(
    student_id: int,
    latest_only: bool = Query(True, description="True = solo la más reciente; False = todas"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene evaluación(es) del estudiante (con scales)."""
    try:
        result = PsychopedagogicalEvaluationClass(db).get_by_student_id(
            student_id=student_id, latest_only=latest_only
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error"), "data": None},
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


@psychopedagogical_evaluations.get("/{id}")
def get_by_id(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene una evaluación por id (incluye scales)."""
    try:
        result = PsychopedagogicalEvaluationClass(db).get_by_id(id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "No encontrado"), "data": None},
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


@psychopedagogical_evaluations.post("/store")
def store(
    data: StorePsychopedagogicalEvaluationInfo,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea o actualiza evaluación psicopedagógica: si ya existe una para el estudiante, se actualiza; si no, se crea."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        result = PsychopedagogicalEvaluationClass(db).store(payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": 400, "message": result.get("message", "Error al guardar"), "data": None},
            )
        data_out = result.get("data") if result.get("data") is not None else {"id": result.get("id")}
        is_created = result.get("created", True)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED if is_created else status.HTTP_200_OK,
            content={
                "status": 201 if is_created else 200,
                "message": result.get("message", "Evaluación creada" if is_created else "Evaluación actualizada"),
                "data": data_out,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@psychopedagogical_evaluations.put("/{id}")
def update(
    id: int,
    data: UpdatePsychopedagogicalEvaluationInfo,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza evaluación por id (opcional: scales reemplazan los existentes)."""
    try:
        payload = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else {
            k: v for k, v in data.dict().items() if v is not None
        }
        result = PsychopedagogicalEvaluationClass(db).update(id, payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "No encontrado"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "OK"), "data": result.get("data")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@psychopedagogical_evaluations.delete("/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Elimina evaluación por id (y sus scales)."""
    try:
        result = PsychopedagogicalEvaluationClass(db).delete(id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "No encontrado")},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Evaluación eliminada")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e)},
        )
