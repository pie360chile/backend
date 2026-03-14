"""Router: document_alerts."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.backend.auth.auth_user import get_current_active_user
from app.backend.db.database import get_db
from app.backend.schemas import UserLogin, StoreDocumentAlert, UpdateDocumentAlert
from app.backend.classes.document_alert_class import DocumentAlertClass

document_alerts = APIRouter(
    prefix="/document_alerts",
    tags=["Document Alerts"],
)


@document_alerts.get("")
def list_document_alerts(
    student_id: Optional[int] = Query(None, description="Filtrar por estudiante"),
    professional_id: Optional[int] = Query(None, description="Filtrar por profesional"),
    document_id: Optional[int] = Query(None, description="Filtrar por documento"),
    include_deleted: bool = Query(False, description="Incluir eliminados (soft)"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista registros de document_alerts con filtros opcionales."""
    try:
        result = DocumentAlertClass(db).get(
            student_id=student_id,
            professional_id=professional_id,
            document_id=document_id,
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


@document_alerts.get("/{id}")
def get_document_alert(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene un registro por id."""
    try:
        result = DocumentAlertClass(db).get_by_id(id)
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


@document_alerts.post("/store")
def store_document_alert(
    data: StoreDocumentAlert,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea un registro en document_alerts."""
    try:
        result = DocumentAlertClass(db).store(data.model_dump())
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


@document_alerts.put("/{id}")
def update_document_alert(
    id: int,
    data: UpdateDocumentAlert,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza un registro por id."""
    try:
        payload = data.model_dump(exclude_unset=True)
        result = DocumentAlertClass(db).update(id, payload)
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


@document_alerts.delete("/{id}")
def delete_document_alert(
    id: int,
    soft: bool = Query(True, description="True = soft delete (deleted_date)"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Elimina un registro por id (soft o físico)."""
    try:
        result = DocumentAlertClass(db).delete(id, soft=soft)
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
