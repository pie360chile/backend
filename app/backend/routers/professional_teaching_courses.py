from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StoreProfessionalTeachingCourse, UpdateProfessionalTeachingCourse
from app.backend.classes.professional_teaching_course_class import ProfessionalTeachingCourseClass
from sqlalchemy.orm import Session
from typing import Optional

professional_teaching_courses = APIRouter(
    prefix="/professional_teaching_courses",
    tags=["Professional Teaching Courses (assign)"],
)


@professional_teaching_courses.get("/by_teacher_type/{teacher_type_id}/{course_id}")
def get_by_teacher_type(
    teacher_type_id: int,
    course_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista asignaciones por tipo de profesional (regular/especialista por id) y course_id. Solo deleted_status_id == 0."""
    try:
        result = ProfessionalTeachingCourseClass(db).get_by_teacher_type(teacher_type_id, course_id)
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
            content={
                "status": 500,
                "message": str(e),
                "data": [],
            },
        )


@professional_teaching_courses.get("/{professional_id}/{teaching_id}/{course_id}/{teacher_type_id}/{deleted_status_id}")
def get_list(
    professional_id: int,
    teaching_id: int,
    course_id: int,
    teacher_type_id: int,
    deleted_status_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista asignaciones profesional-enseñanza-curso. Filtros en URL: professional_id, teaching_id, course_id, teacher_type_id, deleted_status_id (usar -1 para no filtrar por ese campo)."""
    try:
        result = ProfessionalTeachingCourseClass(db).get(
            professional_id=professional_id,
            teaching_id=teaching_id,
            course_id=course_id,
            teacher_type_id=teacher_type_id,
            deleted_status_id=deleted_status_id,
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


@professional_teaching_courses.get("/{id}")
def get_by_id(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene una asignación por id (valor en la URL)."""
    try:
        result = ProfessionalTeachingCourseClass(db).get_by_id(id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Asignación no encontrada"),
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


@professional_teaching_courses.put("/{id}")
def edit(
    id: int,
    data: UpdateProfessionalTeachingCourse,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Edita una asignación por id (valor en la URL)."""
    try:
        payload = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else {k: v for k, v in data.dict().items() if v is not None}
        result = ProfessionalTeachingCourseClass(db).update(id, payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND if "no encontrada" in result.get("message", "") else status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 404 if "no encontrada" in result.get("message", "") else 500,
                    "message": result.get("message"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Asignación actualizada correctamente"),
                "data": result.get("data"),
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@professional_teaching_courses.post("/store")
def store(
    data: StoreProfessionalTeachingCourse,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea una asignación profesional - enseñanza - curso (una fila en professionals_teachings_courses)."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        result = ProfessionalTeachingCourseClass(db).store(payload)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error al guardar asignación"),
                    "data": None,
                },
            )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "Asignación creada correctamente"),
                "data": {"id": result.get("id")},
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error creando asignación: {str(e)}",
                "data": None,
            },
        )


@professional_teaching_courses.delete("/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Elimina una asignación por ID (borrado lógico: actualiza deleted_status_id = 1)."""
    try:
        result = ProfessionalTeachingCourseClass(db).delete(id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Asignación no encontrada"),
                    "data": None,
                },
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Asignación eliminada correctamente"),
                "data": None,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error eliminando asignación: {str(e)}",
                "data": None,
            },
        )
