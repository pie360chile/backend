"""Plantillas/modelos descargables para documentos de solo carga."""

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.document_format_models_class import DocumentFormatModelsClass
from app.backend.core.responses import api_error, api_response
from app.backend.db.database import get_db
from app.backend.db.models import RolModel, UserModel

document_format_models = APIRouter(
    prefix="/document-format-models",
    tags=["Document format models"],
)


def _can_manage_models(session_user: UserModel, db: Session) -> bool:
    """Administrador de establecimiento, coordinador o evaluador (por cliente). No superadmin."""
    rid = int(getattr(session_user, "rol_id", 0) or 0)
    if rid == 1:
        return False
    if rid == 2:
        return True
    rol = db.query(RolModel).filter(RolModel.id == session_user.rol_id).first()
    if not rol or not rol.rol:
        return False
    n = str(rol.rol).lower()
    if "coordinador" in n or "evaluador" in n:
        return True
    if "administrador" in n and "super" not in n:
        return True
    return False


@document_format_models.get("")
def list_format_models(
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    if not _can_manage_models(session_user, db):
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="No tienes permiso para gestionar modelos de documentos.",
        )
    data = DocumentFormatModelsClass(db).list_items()
    return api_response(data=data)


@document_format_models.get("/{document_id}")
def get_format_model_meta(
    document_id: int,
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    _ = session_user
    row = DocumentFormatModelsClass(db).get_model(document_id)
    if not row:
        return api_response(
            data={
                "document_id": int(document_id),
                "has_model": False,
                "original_filename": None,
            }
        )
    return api_response(
        data={
            "document_id": int(document_id),
            "has_model": True,
            "original_filename": row.original_filename,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
    )


@document_format_models.get("/{document_id}/download")
def download_format_model(
    document_id: int,
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    # Cualquier usuario autenticado puede descargar el modelo (p. ej. al llenar ficha).
    _ = session_user
    svc = DocumentFormatModelsClass(db)
    row = svc.get_model(document_id)
    if not row:
        return api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No hay modelo cargado para este documento.",
        )
    path = svc.absolute_path(row)
    if not path:
        return api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Archivo del modelo no encontrado.",
        )
    return FileResponse(
        path,
        filename=row.original_filename or path.name,
        media_type=row.content_type or "application/octet-stream",
    )


@document_format_models.post("/{document_id}")
async def upload_format_model(
    document_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    if not _can_manage_models(session_user, db):
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="No tienes permiso para cargar modelos de documentos.",
        )
    data = await file.read()
    result = DocumentFormatModelsClass(db).upload(
        document_id,
        file.filename or "modelo.docx",
        data,
        file.content_type,
        int(session_user.id) if getattr(session_user, "id", None) else None,
    )
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


@document_format_models.delete("/{document_id}")
def delete_format_model(
    document_id: int,
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    if not _can_manage_models(session_user, db):
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="No tienes permiso para eliminar modelos de documentos.",
        )
    result = DocumentFormatModelsClass(db).delete(document_id)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_404_NOT_FOUND),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"))
