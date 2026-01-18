from fastapi import APIRouter, status, Depends, Body
from fastapi.responses import JSONResponse
from app.backend.classes.health_evaluation_class import HealthEvaluationClass
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StoreHealthEvaluation
from typing import Optional
from sqlalchemy.orm import Session

health_evaluations = APIRouter(
    prefix="/health_evaluations",
    tags=["Health Evaluations"]
)

@health_evaluations.post("/store")
async def store_health_evaluation(
    evaluation_data: StoreHealthEvaluation,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Crea una nueva evaluación de salud.
    """
    try:
        health_evaluation_service = HealthEvaluationClass(db)
        result = health_evaluation_service.store(evaluation_data.dict())

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error guardando evaluación de salud"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "Evaluación de salud creada exitosamente"),
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
                "message": f"Error creando evaluación de salud: {str(e)}",
                "data": None
            }
        )

@health_evaluations.get("/{id}")
async def get_health_evaluation(
    id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene una evaluación de salud por su ID.
    """
    try:
        health_evaluation_service = HealthEvaluationClass(db)
        result = health_evaluation_service.get(id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Evaluación de salud no encontrada"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Evaluación de salud encontrada",
                "data": result
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo evaluación de salud: {str(e)}",
                "data": None
            }
        )

@health_evaluations.get("/list")
async def list_health_evaluations(
    student_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Lista las evaluaciones de salud almacenadas.
    Puede filtrarse por student_id.
    """
    try:
        health_evaluation_service = HealthEvaluationClass(db)
        data = health_evaluation_service.get_all(student_id)

        if isinstance(data, dict) and data.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": data.get("message", "Error listando evaluaciones de salud"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Evaluaciones de salud encontradas" if data else "No hay evaluaciones de salud registradas",
                "data": data
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error listando evaluaciones de salud: {str(e)}",
                "data": None
            }
        )
