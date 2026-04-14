from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Any, List, Optional

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.audit_class import AuditClass
from app.backend.db.database import get_db
from app.backend.db.models import EvaluatorChatAuditModel
from app.backend.schemas import StoreAudit, UserLogin

audits = APIRouter(
    prefix="/audits",
    tags=["Audits"]
)


def _user_id_int(session_user: UserLogin) -> int:
    uid_raw = getattr(session_user, "id", None) or getattr(session_user, "user_id", None) or 1
    return int(uid_raw) if uid_raw is not None else 1


def _evaluator_chat_audit_to_dict(r: EvaluatorChatAuditModel) -> dict[str, Any]:
    return {
        "id": r.id,
        "user_id": r.user_id,
        "document_type_id": r.document_type_id,
        "student_id": r.student_id,
        "field_key": r.field_key,
        "question": r.question,
        "added_date": r.added_date.isoformat() if r.added_date else None,
    }


@audits.get(
    "/evaluator-chat",
    summary="Listado de auditoría del chat evaluador",
    description=(
        "Usos del chat evaluador del usuario autenticado. "
        "Filtros opcionales: student_id, document_type_id. Paginación: limit (máx. 200), offset."
    ),
)
def list_evaluator_chat_audits(
    student_id: Optional[int] = Query(None, ge=1, description="Filtrar por estudiante"),
    document_type_id: Optional[int] = Query(None, ge=1, description="Filtrar por tipo de documento"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        uid = _user_id_int(session_user)
        q = db.query(EvaluatorChatAuditModel).filter(EvaluatorChatAuditModel.user_id == uid)
        if student_id is not None:
            q = q.filter(EvaluatorChatAuditModel.student_id == student_id)
        if document_type_id is not None:
            q = q.filter(EvaluatorChatAuditModel.document_type_id == document_type_id)
        total = q.count()
        rows: List[EvaluatorChatAuditModel] = (
            q.order_by(EvaluatorChatAuditModel.id.desc()).offset(offset).limit(limit).all()
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "OK",
                "data": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "items": [_evaluator_chat_audit_to_dict(r) for r in rows],
                },
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
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
