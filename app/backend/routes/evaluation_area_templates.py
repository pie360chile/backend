"""Plantillas personalizadas por área de evaluación."""

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.evaluation_area_templates_class import EvaluationAreaTemplatesClass
from app.backend.core.responses import api_error, api_response
from app.backend.db.database import get_db
from app.backend.db.models import RolModel, UserModel

evaluation_area_templates = APIRouter(
    prefix="/evaluation-area-templates",
    tags=["Evaluation area templates"],
)


def _can_manage_templates(session_user: UserModel, db: Session) -> bool:
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


def _customer_id(session_user: UserModel) -> int:
    return int(getattr(session_user, "customer_id", 0) or 0)


@evaluation_area_templates.get("")
def list_templates(
    area_id: str | None = None,
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    data = EvaluationAreaTemplatesClass(db).list_items(_customer_id(session_user), area_id)
    return api_response(data=data)


@evaluation_area_templates.post("")
async def create_template(
    area_id: str = Form(...),
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    if not _can_manage_templates(session_user, db):
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="No tienes permiso para crear plantillas.",
        )
    data = await file.read()
    result = EvaluationAreaTemplatesClass(db).create(
        customer_id=_customer_id(session_user),
        area_id=(area_id or "").strip(),
        name=name,
        filename=file.filename or "plantilla.docx",
        data=data,
        content_type=file.content_type,
        user_id=int(session_user.id) if getattr(session_user, "id", None) else None,
    )
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


@evaluation_area_templates.post("/{template_id}")
async def replace_template_file(
    template_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    if not _can_manage_templates(session_user, db):
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="No tienes permiso para actualizar plantillas.",
        )
    data = await file.read()
    result = EvaluationAreaTemplatesClass(db).replace_file(
        template_id,
        _customer_id(session_user),
        file.filename or "plantilla.docx",
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


@evaluation_area_templates.get("/{template_id}/download")
def download_template(
    template_id: int,
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    svc = EvaluationAreaTemplatesClass(db)
    row = svc.get_row(template_id, _customer_id(session_user))
    if not row:
        return api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No hay plantilla cargada.",
        )
    path = svc.absolute_path(row)
    if not path:
        return api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Archivo de la plantilla no encontrado.",
        )
    return FileResponse(
        path,
        filename=row.original_filename or path.name,
        media_type=row.content_type or "application/octet-stream",
    )


@evaluation_area_templates.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    if not _can_manage_templates(session_user, db):
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="No tienes permiso para eliminar plantillas.",
        )
    result = EvaluationAreaTemplatesClass(db).delete(template_id, _customer_id(session_user))
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_404_NOT_FOUND),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"))
