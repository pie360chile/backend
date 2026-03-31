from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import (
    UserLogin,
    StoreRegularTeacherDiversifiedStrategy,
    UpdateRegularTeacherDiversifiedStrategy,
)
from app.backend.classes.regular_teacher_diversified_strategy_class import (
    RegularTeacherDiversifiedStrategyClass,
)
from sqlalchemy.orm import Session
from typing import Optional

regular_teacher_diversified_strategies = APIRouter(
    prefix="/regular_teacher_diversified_strategies",
    tags=["Regular Teacher Diversified Strategies"],
)


@regular_teacher_diversified_strategies.get("")
def get_list(
    school_id: Optional[int] = Query(None, description="-1 o omitir = no filtrar"),
    course_id: Optional[int] = Query(None, description="-1 o omitir = no filtrar"),
    subject_id: Optional[int] = Query(None, description="-1 o omitir = no filtrar"),
    period_id: Optional[int] = Query(None, description="1, 2 o 3 — filtrar por pestaña de período"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista registros. Filtros opcionales por school_id, course_id, subject_id y period_id."""
    try:
        result = RegularTeacherDiversifiedStrategyClass(db).get(
            school_id=school_id, course_id=course_id, subject_id=subject_id, period_id=period_id
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error al listar"),
                    "data": result.get("data", []),
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "OK",
                "data": result.get("data", []),
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": str(e),
                "data": [],
            },
        )


@regular_teacher_diversified_strategies.get("/by_course/{course_id}")
def get_by_course_id(
    course_id: int,
    period_id: Optional[int] = Query(None, description="1, 2 o 3 — filtrar por pestaña de período"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene registros del curso; con period_id solo los de ese período (p. ej. pestaña 2do)."""
    try:
        result = RegularTeacherDiversifiedStrategyClass(db).get_by_course_id(
            course_id=course_id, period_id=period_id
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error al listar"),
                    "data": [],
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "OK",
                "data": result.get("data", []),
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": []},
        )


@regular_teacher_diversified_strategies.get("/{id}")
def get_by_id(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene un registro por id (pk)."""
    try:
        result = RegularTeacherDiversifiedStrategyClass(db).get_by_id(id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Registro no encontrado"),
                    "data": None,
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
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@regular_teacher_diversified_strategies.post("/store")
def store(
    data: StoreRegularTeacherDiversifiedStrategy,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea un nuevo registro. school_id del body o de la sesión del usuario."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        if payload.get("school_id") is None and getattr(session_user, "school_id", None) is not None:
            payload["school_id"] = session_user.school_id
        result = RegularTeacherDiversifiedStrategyClass(db).store(payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error al guardar"),
                    "data": None,
                },
            )
        created = result.get("data")
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "Registro creado"),
                "data": created if created is not None else {"id": result.get("id")},
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": str(e),
                "data": None,
            },
        )


@regular_teacher_diversified_strategies.put("/{id}")
def update(
    id: int,
    data: UpdateRegularTeacherDiversifiedStrategy,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza un registro por id."""
    try:
        payload = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else {k: v for k, v in data.dict().items() if v is not None}
        result = RegularTeacherDiversifiedStrategyClass(db).update(id, payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Registro no encontrado"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Registro actualizado"),
                "data": {"id": result.get("id")},
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": str(e),
                "data": None,
            },
        )


@regular_teacher_diversified_strategies.delete("/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Elimina físicamente el registro."""
    try:
        result = RegularTeacherDiversifiedStrategyClass(db).delete(id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Registro no encontrado"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Registro eliminado"),
                "data": None,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": str(e),
                "data": None,
            },
        )
