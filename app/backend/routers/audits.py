from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.backend.db.database import get_db
from app.backend.classes.audit_class import AuditClass
from app.backend.schemas import StoreAudit, AuditList
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin

audits = APIRouter(
    prefix="/audits",
    tags=["Audits"]
)

@audits.post("")
async def store_audit(
    audit: StoreAudit,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo registro de auditoría (login).
    """
    try:
        audit_service = AuditClass(db)
        result = audit_service.store(
            user_id=audit.user_id,
            rol_id=audit.rol_id
        )

        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": 400,
                    "message": result.get("message", "Error al crear registro de auditoría"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": "Registro de auditoría creado exitosamente",
                "data": result.get("audit_data")
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error creando registro de auditoría: {str(e)}",
                "data": None
            }
        )

@audits.get("/{audit_id}")
async def get_audit(
    audit_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene un registro de auditoría por su ID.
    """
    try:
        audit_service = AuditClass(db)
        result = audit_service.get(audit_id)

        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Registro de auditoría no encontrado"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Registro de auditoría encontrado",
                "data": result.get("audit_data")
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo registro de auditoría: {str(e)}",
                "data": None
            }
        )

@audits.get("")
async def get_all_audits(
    page: int = 0,
    per_page: int = 10,
    user_id: Optional[int] = None,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los registros de auditoría, opcionalmente filtrados por user_id.
    """
    try:
        audit_service = AuditClass(db)
        result = audit_service.get_all(user_id=user_id, page=page, items_per_page=per_page)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": 400,
                    "message": result.get("message", "Error al obtener registros de auditoría"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Registros de auditoría obtenidos exitosamente",
                "data": result
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo registros de auditoría: {str(e)}",
                "data": None
            }
        )
