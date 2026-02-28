"""Router: Card 3 - Registro de logros de aprendizaje por curso, estudiante y período."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import (
    UserLogin,
    StoreCourseLearningAchievement,
    UpdateCourseLearningAchievement,
)
from app.backend.classes.course_learning_achievement_class import CourseLearningAchievementClass
from sqlalchemy.orm import Session
from typing import Optional

course_learning_achievements = APIRouter(
    prefix="/course_learning_achievements",
    tags=["Course Learning Achievements (Card 3)"],
)


@course_learning_achievements.get("/by_course/{course_id}")
def get_by_course_id(
    course_id: int,
    period_id: Optional[int] = Query(None, description="Filtrar por período: 1, 2 o 3"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista logros del curso; opcionalmente por period_id (1, 2, 3)."""
    try:
        result = CourseLearningAchievementClass(db).get_by_course_id(course_id=course_id, period_id=period_id)
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


@course_learning_achievements.get("/by_course_student_period")
def get_by_course_student_period(
    course_id: int = Query(..., description="ID del curso"),
    student_id: int = Query(..., description="ID del estudiante"),
    period_id: int = Query(..., description="1, 2 o 3"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene el registro de logros por (course_id, student_id, period_id)."""
    try:
        result = CourseLearningAchievementClass(db).get_by_course_student_period(
            course_id=course_id, student_id=student_id, period_id=period_id
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": 400, "message": result.get("message", "Error"), "data": None},
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


@course_learning_achievements.get("/{id}")
def get_by_id(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene un registro de logros por id."""
    try:
        result = CourseLearningAchievementClass(db).get_by_id(id)
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


@course_learning_achievements.post("/store")
def store(
    data: StoreCourseLearningAchievement,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea o actualiza logros por (course_id, student_id, period_id). period_id: 1, 2 o 3."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        result = CourseLearningAchievementClass(db).store(payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": 400, "message": result.get("message", "Error al guardar"), "data": None},
            )
        data_out = result.get("data") if result.get("data") is not None else {"id": result.get("id")}
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": 201, "message": result.get("message", "Registro guardado"), "data": data_out},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@course_learning_achievements.put("/{id}")
def update(
    id: int,
    data: UpdateCourseLearningAchievement,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza un registro por id (achievements, comments)."""
    try:
        payload = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else {k: v for k, v in data.dict().items() if v is not None}
        result = CourseLearningAchievementClass(db).update(id, payload)
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


@course_learning_achievements.delete("/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Elimina un registro por id."""
    try:
        result = CourseLearningAchievementClass(db).delete(id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "No encontrado")},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Registro eliminado")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e)},
        )
