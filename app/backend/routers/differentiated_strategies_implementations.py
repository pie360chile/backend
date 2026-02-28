"""Router: differentiated_strategies_implementations."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import (
    UserLogin,
    StoreDifferentiatedStrategiesImplementation,
    UpdateDifferentiatedStrategiesImplementation,
)
from app.backend.classes.differentiated_strategies_implementation_class import DifferentiatedStrategiesImplementationClass
from sqlalchemy.orm import Session
from typing import Optional

differentiated_strategies_implementations = APIRouter(
    prefix="/differentiated_strategies_implementations",
    tags=["Differentiated Strategies Implementations"],
)


@differentiated_strategies_implementations.get("")
def get_list(
    page: Optional[int] = Query(0, description="0 = sin paginación"),
    per_page: Optional[int] = Query(100, description="Registros por página"),
    actions_taken: Optional[str] = Query(None, description="Filtrar por acciones realizadas"),
    applied_strategies: Optional[str] = Query(None, description="Filtrar por estrategias aplicadas"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista implementaciones de estrategias diversificadas activas (deleted_date is None)."""
    try:
        result = DifferentiatedStrategiesImplementationClass(db).get_all(
            page=page or 0,
            items_per_page=per_page or 100,
            actions_taken=actions_taken,
            applied_strategies=applied_strategies,
        )
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error"), "data": []},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": result},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": []},
        )


@differentiated_strategies_implementations.get("/{id}")
def get_by_id(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene una implementación por id."""
    try:
        result = DifferentiatedStrategiesImplementationClass(db).get(id)
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


@differentiated_strategies_implementations.post("/store")
def store(
    data: StoreDifferentiatedStrategiesImplementation,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea una implementación (actions_taken, applied_strategies)."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        result = DifferentiatedStrategiesImplementationClass(db).store(payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error al guardar"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": 201, "message": result.get("message", "Creado"), "data": {"id": result.get("id")}},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@differentiated_strategies_implementations.put("/{id}")
def update(
    id: int,
    data: UpdateDifferentiatedStrategiesImplementation,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza una implementación por id (opcional: actions_taken, applied_strategies)."""
    try:
        payload = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else {k: v for k, v in data.dict().items() if v is not None}
        result = DifferentiatedStrategiesImplementationClass(db).update(id, payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Registro no encontrado"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Actualizado"), "data": {"id": id}},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@differentiated_strategies_implementations.delete("/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Borrado lógico (deleted_date)."""
    try:
        result = DifferentiatedStrategiesImplementationClass(db).delete(id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Registro no encontrado"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Eliminado"), "data": None},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )
