"""Router: Card 2 - Registro de apoyos por curso y área (objetivos, estudiantes, intervenciones)."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import (
    UserLogin,
    StoreCourseRecordSupport,
    UpdateCourseRecordSupport,
    StoreCourseRecordSupportIntervention,
    UpdateCourseRecordSupportIntervention,
)
from app.backend.classes.course_record_support_class import CourseRecordSupportClass
from sqlalchemy.orm import Session

course_record_supports = APIRouter(
    prefix="/course_record_supports",
    tags=["Course Record Supports (Card 2)"],
)


@course_record_supports.get("/by_course/{course_id}")
def get_by_course_id(
    course_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista por curso: todas las áreas con registro (objetivos, student_ids, interventions)."""
    try:
        result = CourseRecordSupportClass(db).get_by_course_id(course_id=course_id)
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


@course_record_supports.post("/record")
def save_record(
    data: StoreCourseRecordSupport,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Guarda registro por curso y área: objetivos de aprendizaje + estudiantes que recibirán los apoyos."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        result = CourseRecordSupportClass(db).save_record(payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error al guardar"), "data": None},
            )
        data_out = result.get("data") if result.get("data") is not None else {"id": result.get("id")}
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Datos guardados"), "data": data_out},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@course_record_supports.get("/interventions")
def get_interventions(
    course_id: int = Query(..., description="ID del curso"),
    support_area_id: int = Query(..., description="ID del área de apoyo"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista intervenciones (Ingresar apoyo) por curso y área."""
    try:
        result = CourseRecordSupportClass(db).get_interventions(course_id=course_id, support_area_id=support_area_id)
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


@course_record_supports.get("/interventions/{id}")
def get_intervention_by_id(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene una intervención por id."""
    try:
        result = CourseRecordSupportClass(db).get_intervention_by_id(id)
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


@course_record_supports.post("/interventions/store")
def store_intervention(
    data: StoreCourseRecordSupportIntervention,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea una intervención (Ingresar apoyo): fecha, horas pedagógicas, lugar, profesional, actividades desarrolladas."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        result = CourseRecordSupportClass(db).store_intervention(payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": 400, "message": result.get("message", "Error al guardar"), "data": None},
            )
        data_out = result.get("data") if result.get("data") is not None else {"id": result.get("id")}
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": 201, "message": result.get("message", "Apoyo registrado"), "data": data_out},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@course_record_supports.put("/interventions/{id}")
def update_intervention(
    id: int,
    data: UpdateCourseRecordSupportIntervention,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza una intervención por id."""
    try:
        payload = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else {k: v for k, v in data.dict().items() if v is not None}
        result = CourseRecordSupportClass(db).update_intervention(id, payload)
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


@course_record_supports.delete("/interventions/{id}")
def delete_intervention(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Elimina una intervención por id."""
    try:
        result = CourseRecordSupportClass(db).delete_intervention(id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "No encontrado")},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Intervención eliminada")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e)},
        )
