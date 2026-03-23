from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin
from app.backend.classes.diversity_strategy_option_class import DiversityStrategyOptionClass
from sqlalchemy.orm import Session
from typing import Optional

diversity_strategy_options = APIRouter(
    prefix="/diversity_strategy_options",
    tags=["Diversity Strategy Options"],
)


@diversity_strategy_options.get("")
def get_list(
    diversity_criterion_id: Optional[int] = Query(None, description="-1 o omitir = no filtrar"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista opciones de estrategia activas. Filtro opcional por diversity_criterion_id."""
    try:
        result = DiversityStrategyOptionClass(db).get(diversity_criterion_id=diversity_criterion_id)
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


@diversity_strategy_options.get("/{id}")
def get_by_id(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene una opción por id."""
    try:
        result = DiversityStrategyOptionClass(db).get_by_id(id)
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
