from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from app.backend.classes.progress_status_student_class import ProgressStatusStudentClass
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StoreProgressStatusStudent, UpdateProgressStatusStudent, ProgressStatusStudentList
from typing import Optional
from sqlalchemy.orm import Session

progress_status_students = APIRouter(
    prefix="/progress_status_students",
    tags=["Progress Status Students"]
)

@progress_status_students.post("/store")
async def store_progress_status_student(
    progress_status_data: StoreProgressStatusStudent,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo estado de avance (Documento 18).
    """
    try:
        progress_status_service = ProgressStatusStudentClass(db)
        result = progress_status_service.store(progress_status_data.dict())

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error guardando estado de avance"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "Estado de avance creado exitosamente"),
                "data": {
                    "id": result.get("id")
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error creando estado de avance: {str(e)}",
                "data": None
            }
        )

@progress_status_students.get("/{id}")
async def get_progress_status_student(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene un estado de avance por su ID.
    """
    try:
        progress_status_service = ProgressStatusStudentClass(db)
        result = progress_status_service.get(id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Estado de avance no encontrado"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Estado de avance encontrado",
                "data": result
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo estado de avance: {str(e)}",
                "data": None
            }
        )

@progress_status_students.post("/")
async def list_progress_status_students(
    progress_status_list: ProgressStatusStudentList = ProgressStatusStudentList(),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lista los estados de avance almacenados.
    Puede filtrarse por student_id y school_id.
    """
    try:
        progress_status_service = ProgressStatusStudentClass(db)
        data = progress_status_service.get_all(
            student_id=progress_status_list.student_id,
            school_id=progress_status_list.school_id
        )

        if isinstance(data, dict) and data.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": data.get("message", "Error listando estados de avance"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Estados de avance encontrados" if data else "No hay estados de avance registrados",
                "data": data
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error listando estados de avance: {str(e)}",
                "data": None
            }
        )

@progress_status_students.put("/{id}")
async def update_progress_status_student(
    id: int,
    progress_status_data: UpdateProgressStatusStudent,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza un estado de avance existente.
    """
    try:
        progress_status_service = ProgressStatusStudentClass(db)
        result = progress_status_service.update(id, progress_status_data.dict(exclude_unset=True))

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Error actualizando estado de avance"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Estado de avance actualizado exitosamente"),
                "data": {
                    "id": result.get("id")
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error actualizando estado de avance: {str(e)}",
                "data": None
            }
        )

@progress_status_students.delete("/{id}")
async def delete_progress_status_student(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Elimina lógicamente un estado de avance (soft delete).
    """
    try:
        progress_status_service = ProgressStatusStudentClass(db)
        result = progress_status_service.delete(id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Error eliminando estado de avance"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Estado de avance eliminado exitosamente"),
                "data": None
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error eliminando estado de avance: {str(e)}",
                "data": None
            }
        )
