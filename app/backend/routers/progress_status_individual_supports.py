from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from app.backend.classes.progress_status_individual_support_class import ProgressStatusIndividualSupportClass
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StoreProgressStatusIndividualSupport, UpdateProgressStatusIndividualSupport, ProgressStatusIndividualSupportList
from typing import Optional
from sqlalchemy.orm import Session

progress_status_individual_supports = APIRouter(
    prefix="/progress_status_individual_supports",
    tags=["Progress Status Individual Supports"]
)

@progress_status_individual_supports.post("/store")
async def store_progress_status_individual_support(
    data: StoreProgressStatusIndividualSupport,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo estado de avance PAI (Documento 19).
    """
    try:
        service = ProgressStatusIndividualSupportClass(db)
        result = service.store(data.dict())

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error guardando estado de avance PAI"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "Estado de avance PAI creado exitosamente"),
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
                "message": f"Error creando estado de avance PAI: {str(e)}",
                "data": None
            }
        )

@progress_status_individual_supports.get("/{id}")
async def get_progress_status_individual_support(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene un estado de avance PAI por su ID.
    """
    try:
        service = ProgressStatusIndividualSupportClass(db)
        result = service.get(id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Estado de avance PAI no encontrado"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Estado de avance PAI encontrado",
                "data": result
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo estado de avance PAI: {str(e)}",
                "data": None
            }
        )

@progress_status_individual_supports.get("/student/{student_id}")
async def get_progress_status_individual_support_by_student(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene el último estado de avance PAI por el ID del estudiante.
    """
    try:
        service = ProgressStatusIndividualSupportClass(db)
        result = service.get_by_student_id(student_id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Estado de avance PAI no encontrado para el estudiante"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Estado de avance PAI encontrado",
                "data": result
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo estado de avance PAI: {str(e)}",
                "data": None
            }
        )

@progress_status_individual_supports.post("/")
async def list_progress_status_individual_supports(
    filters: ProgressStatusIndividualSupportList = ProgressStatusIndividualSupportList(),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lista los estados de avance PAI almacenados.
    Puede filtrarse por student_id y school_id.
    """
    try:
        service = ProgressStatusIndividualSupportClass(db)
        data = service.get_all(
            student_id=filters.student_id,
            school_id=filters.school_id
        )

        if isinstance(data, dict) and data.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": data.get("message", "Error listando estados de avance PAI"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Estados de avance PAI encontrados" if data else "No hay estados de avance PAI registrados",
                "data": data
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error listando estados de avance PAI: {str(e)}",
                "data": None
            }
        )

@progress_status_individual_supports.put("/{id}")
async def update_progress_status_individual_support(
    id: int,
    data: UpdateProgressStatusIndividualSupport,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza un estado de avance PAI existente.
    """
    try:
        service = ProgressStatusIndividualSupportClass(db)
        result = service.update(id, data.dict(exclude_unset=True))

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Error actualizando estado de avance PAI"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Estado de avance PAI actualizado exitosamente"),
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
                "message": f"Error actualizando estado de avance PAI: {str(e)}",
                "data": None
            }
        )

@progress_status_individual_supports.delete("/{id}")
async def delete_progress_status_individual_support(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Elimina lógicamente un estado de avance PAI (soft delete).
    """
    try:
        service = ProgressStatusIndividualSupportClass(db)
        result = service.delete(id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Error eliminando estado de avance PAI"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Estado de avance PAI eliminado exitosamente"),
                "data": None
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error eliminando estado de avance PAI: {str(e)}",
                "data": None
            }
        )
