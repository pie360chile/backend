from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StoreFurForm
from app.backend.classes.fur_form_class import FurFormClass

fur_forms = APIRouter(
    prefix="/fur_forms",
    tags=["FUR Forms"],
)


@fur_forms.post("/store")
async def store_fur_form(
    data: StoreFurForm,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea un nuevo FUR (Documento 6)."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        service = FurFormClass(db)
        result = service.store(payload)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error guardando FUR"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": 201, "message": result.get("message", "Formulario FUR guardado."), "data": {"id": result.get("id")}},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@fur_forms.get("/student/{student_id}")
async def get_fur_form_by_student(
    student_id: int,
    fur_variant: Optional[str] = Query(None, description="Variante FUR, ej. dea"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene el último FUR por estudiante (opcionalmente por variante)."""
    try:
        service = FurFormClass(db)
        result = service.get_by_student_id(student_id, fur_variant=fur_variant)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "FUR no encontrado."), "data": None},
            )
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": "OK", "data": result})
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@fur_forms.put("/{id}")
async def update_fur_form(
    id: int,
    data: StoreFurForm,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza un FUR existente."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        service = FurFormClass(db)
        result = service.update(id, payload)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "FUR no encontrado.")},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "OK"), "data": {"id": result.get("id")}},
        )
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e)})
