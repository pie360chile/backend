from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import (
    UserLogin,
    StoreCourseDiversityResponse,
    UpdateCourseDiversityResponse,
    StoreCourseDiversityObservations,
)
from app.backend.classes.course_diversity_response_class import CourseDiversityResponseClass
from sqlalchemy.orm import Session
from typing import Optional

course_diversity_responses = APIRouter(
    prefix="/course_diversity_responses",
    tags=["Course Diversity Responses"],
)


@course_diversity_responses.get("")
def get_list(
    course_id: Optional[int] = Query(None, description="-1 o omitir = no filtrar"),
    include_deleted: bool = Query(False, description="True = incluir registros con deleted_date (todos)"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista respuestas. Filtro opcional por course_id. include_deleted=true devuelve todos los registros."""
    try:
        result = CourseDiversityResponseClass(db).get(course_id=course_id, include_deleted=include_deleted)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error al listar"), "data": []},
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


@course_diversity_responses.get("/by_course/{course_id}")
def get_by_course_id(
    course_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Estructura completa para el curso: criterios, opciones, respuesta por criterio, student_ids y observaciones."""
    try:
        result = CourseDiversityResponseClass(db).get_by_course_id(course_id=course_id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error"), "data": []},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "OK",
                "data": result.get("data", []),
                "observations": result.get("observations"),
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": []},
        )


@course_diversity_responses.get("/observations")
def get_observations(
    course_id: int = Query(..., description="ID del curso"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene las observaciones (estrategias de diversidad) del curso."""
    try:
        result = CourseDiversityResponseClass(db).get_observations(course_id=course_id)
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


@course_diversity_responses.post("/observations")
def store_observations(
    data: StoreCourseDiversityObservations,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Guarda las observaciones (estrategias de diversidad) del curso en course_diversity_observations."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        course_id = int(payload.get("course_id"))
        observations = payload.get("observations")
        result = CourseDiversityResponseClass(db).set_observations(course_id=course_id, observations=observations)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error al guardar"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Observaciones guardadas."), "data": None},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@course_diversity_responses.get("/{id}")
def get_by_id(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene una respuesta por id (incluye student_ids)."""
    try:
        result = CourseDiversityResponseClass(db).get_by_id(id)
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


@course_diversity_responses.post("/store")
def store(
    data: StoreCourseDiversityResponse,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea o actualiza la respuesta para (course_id, diversity_criterion_id). Incluye student_ids."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        result = CourseDiversityResponseClass(db).store(payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error al guardar"), "data": None},
            )
        msg = result.get("message", "Registro creado")
        data_out = result.get("data") if result.get("data") is not None else {"id": result.get("id")}
        # Si fue desmarcado (borrado lógico) o sin registro que borrar, devolver 200
        is_uncheck = "desmarcado" in msg.lower() or "Sin registro que borrar" in msg
        status_code = status.HTTP_200_OK if is_uncheck else status.HTTP_201_CREATED
        return JSONResponse(
            status_code=status_code,
            content={"status": status_code, "message": msg, "data": data_out},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@course_diversity_responses.put("/{id}")
def update(
    id: int,
    data: UpdateCourseDiversityResponse,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza una respuesta por id (opcional: student_ids)."""
    try:
        payload = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else {k: v for k, v in data.dict().items() if v is not None}
        result = CourseDiversityResponseClass(db).update(id, payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Registro no encontrado"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Registro actualizado"), "data": {"id": result.get("id")}},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@course_diversity_responses.delete("/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Borrado lógico de la respuesta."""
    try:
        result = CourseDiversityResponseClass(db).delete(id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Registro no encontrado"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Registro eliminado"), "data": None},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )
