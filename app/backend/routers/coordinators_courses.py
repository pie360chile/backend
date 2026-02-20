from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StoreCoordinatorsCourse, UpdateCoordinatorsCourse
from app.backend.classes.coordinators_course_class import CoordinatorsCourseClass
from sqlalchemy.orm import Session
from typing import Optional

coordinators_courses = APIRouter(
    prefix="/coordinators_courses",
    tags=["Coordinators Courses"],
)


@coordinators_courses.get("")
def get_list(
    course_id: Optional[int] = Query(None, description="-1 o omitir = no filtrar"),
    professional_id: Optional[int] = Query(None, description="-1 o omitir = no filtrar"),
    coordinator_type_id: Optional[int] = Query(None, description="-1 o omitir = no filtrar"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista coordinadores-cursos activos (deleted_date is None). school_id sale de la sesión. Filtros opcionales."""
    try:
        school_id = session_user.school_id if session_user else None
        if school_id is None:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": 200, "message": "OK", "data": []},
            )
        result = CoordinatorsCourseClass(db).get(
            school_id=school_id,
            course_id=course_id,
            professional_id=professional_id,
            coordinator_type_id=coordinator_type_id,
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


@coordinators_courses.get("/{id}")
def get_by_id(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene un registro coordinators_courses por id."""
    try:
        result = CoordinatorsCourseClass(db).get_by_id(id)
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


@coordinators_courses.post("/store")
def store(
    data: StoreCoordinatorsCourse,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea un registro en coordinators_courses. school_id se toma de la sesión."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        payload["school_id"] = session_user.school_id if session_user else None
        if payload.get("school_id") is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": 400,
                    "message": "No hay school_id en la sesión.",
                    "data": None,
                },
            )
        result = CoordinatorsCourseClass(db).store(payload)
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
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "Registro creado"),
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


@coordinators_courses.put("/{id}")
def update(
    id: int,
    data: UpdateCoordinatorsCourse,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza un registro coordinators_courses por id."""
    try:
        payload = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else {k: v for k, v in data.dict().items() if v is not None}
        result = CoordinatorsCourseClass(db).update(id, payload)
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


@coordinators_courses.delete("/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Borrado lógico: setea deleted_date."""
    try:
        result = CoordinatorsCourseClass(db).delete(id)
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
