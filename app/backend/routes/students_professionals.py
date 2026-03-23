"""students_professionals (relación estudiante-profesional con horas)."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.db.database import get_db
from app.backend.schemas import UserLogin, StoreStudentProfessional, UpdateStudentProfessional
from app.backend.classes.student_professional_class import StudentProfessionalClass
from typing import Optional

students_professionals = APIRouter(
    prefix="/students_professionals",
    tags=["Students Professionals"],
)


@students_professionals.get("")
def list_students_professionals(
    student_id: Optional[int] = Query(None, description="Filtrar por estudiante"),
    professional_id: Optional[int] = Query(None, description="Filtrar por profesional"),
    include_deleted: bool = Query(False, description="Incluir registros eliminados (soft)"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista registros de students_professionals. Opcionalmente filtrar por student_id y/o professional_id."""
    try:
        result = StudentProfessionalClass(db).get(
            student_id=student_id,
            professional_id=professional_id,
            include_deleted=include_deleted,
        )
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


@students_professionals.get("/by_student_career")
def get_by_student_and_career_type(
    student_id: int = Query(..., description="ID del estudiante"),
    career_type_id: int = Query(..., description="ID del tipo de carrera/especialidad"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista profesionales asignados al estudiante para ese career_type_id (solo registros activos, sin deleted_date)."""
    try:
        result = StudentProfessionalClass(db).get_by_student_and_career_type(
            student_id=student_id,
            career_type_id=career_type_id,
        )
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


@students_professionals.get("/{id}")
def get_student_professional(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene un registro por id."""
    try:
        result = StudentProfessionalClass(db).get_by_id(id)
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


@students_professionals.post("/store")
def store_student_professional(
    data: StoreStudentProfessional,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea un registro en students_professionals."""
    try:
        result = StudentProfessionalClass(db).store(data.model_dump())
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": 400, "message": result.get("message", "Error al crear"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": 201, "message": result.get("message", "Creado"), "data": result.get("data"), "id": result.get("id")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@students_professionals.put("/{id}")
def update_student_professional(
    id: int,
    data: UpdateStudentProfessional,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza un registro por id."""
    try:
        payload = data.model_dump(exclude_unset=True)
        result = StudentProfessionalClass(db).update(id, payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "No encontrado")},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Actualizado"), "id": result.get("id")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e)},
        )


@students_professionals.delete("/{id}")
def delete_student_professional(
    id: int,
    soft: bool = Query(True, description="True = soft delete (deleted_date), False = borrado físico"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Elimina un registro por id (soft o físico)."""
    try:
        result = StudentProfessionalClass(db).delete(id, soft=soft)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "No encontrado")},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Eliminado")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e)},
        )
