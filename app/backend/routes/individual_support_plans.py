from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from app.backend.classes.individual_support_plan_class import IndividualSupportPlanClass
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StoreIndividualSupportPlan, UpdateIndividualSupportPlan, IndividualSupportPlanList
from typing import Optional
from sqlalchemy.orm import Session

individual_support_plans = APIRouter(
    prefix="/individual_support_plans",
    tags=["Individual Support Plans"]
)

@individual_support_plans.post("/store")
async def store_individual_support_plan(
    isp_data: StoreIndividualSupportPlan,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo Plan de Apoyo Individual (Documento 22).
    """
    try:
        isp_service = IndividualSupportPlanClass(db)
        data = isp_data.model_dump() if hasattr(isp_data, "model_dump") else isp_data.dict()
        result = isp_service.store(data)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error guardando Plan de Apoyo Individual"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "Plan de Apoyo Individual creado exitosamente"),
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
                "message": f"Error creando Plan de Apoyo Individual: {str(e)}",
                "data": None
            }
        )

@individual_support_plans.get("/list/{student_id}")
async def list_individual_support_plans_by_student(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lista todos los Planes de Apoyo Individual de un estudiante.
    """
    try:
        isp_service = IndividualSupportPlanClass(db)
        data = isp_service.get_all(student_id=student_id, school_id=None)

        if isinstance(data, dict) and data.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": data.get("message", "Error listando Planes de Apoyo Individual"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Planes de Apoyo Individual encontrados" if data else "No hay Planes de Apoyo Individual para este estudiante",
                "data": data
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error listando Planes de Apoyo Individual: {str(e)}",
                "data": None
            }
        )

@individual_support_plans.get("/by-id/{id}")
async def get_individual_support_plan_by_id(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene un Plan de Apoyo Individual por su propio ID.
    """
    try:
        isp_service = IndividualSupportPlanClass(db)
        result = isp_service.get(id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Plan de Apoyo Individual no encontrado"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Plan de Apoyo Individual encontrado",
                "data": result
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo Plan de Apoyo Individual: {str(e)}",
                "data": None
            }
        )

@individual_support_plans.get("/{student_id}")
async def get_individual_support_plan(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene el último Plan de Apoyo Individual por el ID del estudiante.
    """
    try:
        isp_service = IndividualSupportPlanClass(db)
        result = isp_service.get_by_student_id(student_id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Plan de Apoyo Individual no encontrado"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Plan de Apoyo Individual encontrado",
                "data": result
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo Plan de Apoyo Individual: {str(e)}",
                "data": None
            }
        )

@individual_support_plans.post("/")
async def list_individual_support_plans(
    isp_list: IndividualSupportPlanList = IndividualSupportPlanList(),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lista los Planes de Apoyo Individual almacenados.
    Puede filtrarse por student_id y school_id.
    """
    try:
        isp_service = IndividualSupportPlanClass(db)
        data = isp_service.get_all(
            student_id=isp_list.student_id,
            school_id=isp_list.school_id
        )

        if isinstance(data, dict) and data.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": data.get("message", "Error listando Planes de Apoyo Individual"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Planes de Apoyo Individual encontrados" if data else "No hay Planes de Apoyo Individual registrados",
                "data": data
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error listando Planes de Apoyo Individual: {str(e)}",
                "data": None
            }
        )

@individual_support_plans.put("/{id}")
async def update_individual_support_plan(
    id: int,
    isp_data: UpdateIndividualSupportPlan,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza un Plan de Apoyo Individual existente.
    """
    try:
        isp_service = IndividualSupportPlanClass(db)
        data = isp_data.model_dump(exclude_unset=True) if hasattr(isp_data, "model_dump") else isp_data.dict(exclude_unset=True)
        result = isp_service.update(id, data)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Error actualizando Plan de Apoyo Individual"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Plan de Apoyo Individual actualizado exitosamente"),
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
                "message": f"Error actualizando Plan de Apoyo Individual: {str(e)}",
                "data": None
            }
        )

@individual_support_plans.delete("/{id}")
async def delete_individual_support_plan(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Elimina lógicamente un Plan de Apoyo Individual (soft delete).
    """
    try:
        isp_service = IndividualSupportPlanClass(db)
        result = isp_service.delete(id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Error eliminando Plan de Apoyo Individual"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Plan de Apoyo Individual eliminado exitosamente"),
                "data": None
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error eliminando Plan de Apoyo Individual: {str(e)}",
                "data": None
            }
        )
