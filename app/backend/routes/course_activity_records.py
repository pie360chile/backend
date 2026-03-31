"""IV. Registro de actividades (familia/comunidad)."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import (
    UserLogin,
    StoreCourseActivityRecord,
    UpdateCourseActivityRecord,
)
from app.backend.classes.course_activity_record_class import CourseActivityRecordClass
from sqlalchemy.orm import Session
from typing import Optional

course_activity_records = APIRouter(
    prefix="/course_activity_records",
    tags=["Course Activity Records"],
)


@course_activity_records.get("/by_course/{course_id}")
def get_by_course_id(
    course_id: int,
    section: Optional[str] = Query(
        None,
        description="Filtrar por sección: 1=family, 2=community, 3=other (o nombres family|community|other).",
    ),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista registros por curso (y opcionalmente por sección)."""
    try:
        result = CourseActivityRecordClass(db).get_by_course_id(course_id=course_id, section=section)
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


@course_activity_records.get("/{id}")
def get_by_id(
    id: int,
    section: str = Query(
        ...,
        description="Tabla/sección: family | community | other (ids son por tabla).",
    ),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene un registro por id (requiere section: cada sección tiene su propia tabla)."""
    try:
        result = CourseActivityRecordClass(db).get_by_id(id, section)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Registro no encontrado"), "data": None},
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


@course_activity_records.post("/store")
def store(
    data: StoreCourseActivityRecord,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea un registro de actividad."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        result = CourseActivityRecordClass(db).store(payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error al guardar"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": 201, "message": result.get("message", "Registro creado"), "data": result.get("data")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@course_activity_records.put("/{id}")
def update(
    id: int,
    data: UpdateCourseActivityRecord,
    section: str = Query(
        ...,
        description="Tabla/sección: family | community | other.",
    ),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza un registro por id (requiere section)."""
    try:
        payload = (
            data.model_dump(exclude_unset=True)
            if hasattr(data, "model_dump")
            else {k: v for k, v in data.dict().items() if v is not None}
        )
        payload.pop("section", None)
        result = CourseActivityRecordClass(db).update(id, payload, section)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Registro no encontrado"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Registro actualizado"), "data": result.get("data")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@course_activity_records.delete("/{id}")
def delete(
    id: int,
    section: str = Query(
        ...,
        description="Tabla/sección: family | community | other.",
    ),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Elimina un registro por id (requiere section)."""
    try:
        result = CourseActivityRecordClass(db).delete(id, section)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Registro no encontrado")},
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

