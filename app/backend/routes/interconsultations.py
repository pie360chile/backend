from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from app.backend.classes.interconsultation_class import InterconsultationClass
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StoreInterconsultation, UpdateInterconsultation
from typing import Optional
from sqlalchemy.orm import Session

interconsultations = APIRouter(
    prefix="/interconsultations",
    tags=["Interconsultations"]
)


@interconsultations.post("/store")
async def store_interconsultation(
    data: StoreInterconsultation,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Crea una nueva Interconsulta (Documento 24)."""
    try:
        service = InterconsultationClass(db)
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        result = service.store(payload)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error guardando interconsulta"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "Interconsulta creada exitosamente"),
                "data": {"id": result.get("id")}
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error creando interconsulta: {str(e)}",
                "data": None
            }
        )


@interconsultations.get("/list/all")
async def list_interconsultations(
    student_id: Optional[int] = None,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lista interconsultas, opcionalmente filtradas por student_id."""
    try:
        service = InterconsultationClass(db)
        data = service.get_all(student_id=student_id)

        if isinstance(data, dict) and data.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": data.get("message", "Error listando interconsultas"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Interconsultas encontradas" if data else "No hay interconsultas",
                "data": data
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error listando interconsultas: {str(e)}",
                "data": None
            }
        )


@interconsultations.get("/by-student/{student_id}")
async def get_interconsultation_by_student(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtiene la interconsulta más reciente por student_id."""
    try:
        service = InterconsultationClass(db)
        result = service.get_by_student_id(student_id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Interconsulta no encontrada"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Interconsulta encontrada",
                "data": result
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo interconsulta: {str(e)}",
                "data": None
            }
        )


@interconsultations.get("/by-id/{id}")
async def get_interconsultation(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtiene una interconsulta por ID."""
    try:
        service = InterconsultationClass(db)
        result = service.get(id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Interconsulta no encontrada"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Interconsulta encontrada",
                "data": result
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo interconsulta: {str(e)}",
                "data": None
            }
        )


@interconsultations.put("/{id}")
async def update_interconsultation(
    id: int,
    data: UpdateInterconsultation,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Actualiza una interconsulta existente."""
    try:
        service = InterconsultationClass(db)
        payload = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else data.dict(exclude_unset=True)
        result = service.update(id, payload)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Error actualizando interconsulta"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Interconsulta actualizada exitosamente"),
                "data": {"id": result.get("id")}
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error actualizando interconsulta: {str(e)}",
                "data": None
            }
        )


@interconsultations.delete("/{id}")
async def delete_interconsultation(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Elimina una interconsulta."""
    try:
        service = InterconsultationClass(db)
        result = service.delete(id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Interconsulta no encontrada"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Interconsulta eliminada exitosamente"),
                "data": None
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error eliminando interconsulta: {str(e)}",
                "data": None
            }
        )
