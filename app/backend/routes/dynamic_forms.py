"""formularios dinámicos (dynamic_forms)."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.dynamic_form_class import DynamicFormClass
from app.backend.db.database import get_db
from app.backend.schemas import (
    ResendFormWhatsApp,
    StoreDynamicForm,
    SubmitDynamicFormAnswers,
    UpdateDynamicForm,
    UserLogin,
)

dynamic_forms = APIRouter(
    prefix="/dynamic_forms",
    tags=["Dynamic Forms"],
)


def _school_id(user: UserLogin):
    return user.school_id


@dynamic_forms.get("")
def get_list(
    page: int = Query(0, description="0 = sin paginación"),
    per_page: int = Query(100, description="Registros por página"),
    q: Optional[str] = Query(None, description="Buscar en nombre o descripción"),
    period_year: int = Query(..., ge=2000, le=2100, description="Año del período escolar (obligatorio)"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista formularios del colegio del usuario (school_id en token). Filtra por period_year."""
    try:
        sid = _school_id(session_user)
        result = DynamicFormClass(db).get_all(
            page=page or 0,
            items_per_page=per_page or 100,
            search=q,
            school_id=sid,
            period_year=period_year,
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


@dynamic_forms.get("/course_recipients")
def get_course_recipients(
    course_id: int = Query(..., ge=1, description="ID del curso"),
    period_year: Optional[int] = Query(None, description="Año del período escolar (opcional)"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Estudiantes del curso con RUT y datos del apoderado (celular) para notificaciones."""
    try:
        result = DynamicFormClass(db).get_course_recipients(
            course_id,
            session_user.school_id,
            session_user.customer_id,
            period_year=period_year,
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": 400, "message": result.get("message", "Error"), "data": []},
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


@dynamic_forms.get("/{form_id}/students_status")
def students_status(
    form_id: int,
    period_year: int = Query(..., ge=2000, le=2100, description="Año del período escolar"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Estudiantes del curso del formulario con estado respondido / en_espera."""
    try:
        result = DynamicFormClass(db).list_students_status(
            form_id,
            _school_id(session_user),
            getattr(session_user, "customer_id", None),
            period_year,
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": 400,
                    "message": result.get("message", "Error"),
                    "data": result.get("data", []),
                },
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


@dynamic_forms.get("/{form_id}/submissions/{submission_id}")
def get_submission_detail(
    form_id: int,
    submission_id: int,
    period_year: int = Query(..., ge=2000, le=2100, description="Año del período escolar"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        result = DynamicFormClass(db).get_submission_detail(
            form_id,
            submission_id,
            _school_id(session_user),
            getattr(session_user, "customer_id", None),
            period_year=period_year,
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "No encontrado"),
                    "data": None,
                },
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


@dynamic_forms.post("/{form_id}/submit")
def submit_answers(
    form_id: int,
    body: SubmitDynamicFormAnswers,
    period_year: int = Query(..., ge=2000, le=2100, description="Año del período escolar"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        payload = body.model_dump(by_alias=True) if hasattr(body, "model_dump") else body.dict()
        result = DynamicFormClass(db).submit_answers(
            form_id,
            _school_id(session_user),
            getattr(session_user, "customer_id", None),
            int(payload.get("studentId") or payload.get("student_id")),
            payload.get("answers") or {},
            getattr(session_user, "id", None),
            period_year,
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": 400,
                    "message": result.get("message", "Error"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "OK"),
                "data": {"submissionId": result.get("submissionId")},
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@dynamic_forms.post("/{form_id}/resend_whatsapp")
def resend_whatsapp(
    form_id: int,
    body: ResendFormWhatsApp,
    period_year: int = Query(..., ge=2000, le=2100, description="Año del período escolar"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Reenvía la plantilla WhatsApp al apoderado (estudiante en espera, sin respuestas)."""
    try:
        payload = body.model_dump(by_alias=True) if hasattr(body, "model_dump") else body.dict()
        sid = int(payload.get("studentId") or payload.get("student_id"))
        result = DynamicFormClass(db).resend_whatsapp_to_guardian(
            form_id,
            sid,
            _school_id(session_user),
            getattr(session_user, "customer_id", None),
            period_year,
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": 400,
                    "message": result.get("message", "Error"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "OK"),
                "data": {"whatsapp": result.get("whatsapp")},
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@dynamic_forms.get("/{form_id}/student_submission")
def student_submission_lookup(
    form_id: int,
    student_id: int = Query(..., ge=1, description="ID del estudiante"),
    period_year: int = Query(..., ge=2000, le=2100, description="Año del período escolar"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Indica si ya hay respuestas guardadas para ese estudiante (bloquear planilla)."""
    try:
        result = DynamicFormClass(db).submission_for_student(
            form_id,
            student_id,
            _school_id(session_user),
            period_year,
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": 400,
                    "message": result.get("message", "Error"),
                    "data": None,
                },
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


@dynamic_forms.delete("/{form_id}/submissions/{submission_id}")
def delete_submission(
    form_id: int,
    submission_id: int,
    period_year: int = Query(..., ge=2000, le=2100, description="Año del período escolar"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Elimina las respuestas de un estudiante (volver a estado En espera)."""
    try:
        result = DynamicFormClass(db).delete_submission(
            form_id,
            submission_id,
            _school_id(session_user),
            period_year,
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "No encontrado"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "OK"), "data": None},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@dynamic_forms.get("/{id}")
def get_by_id(
    id: int,
    period_year: int = Query(..., ge=2000, le=2100, description="Año del período escolar"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        result = DynamicFormClass(db).get(id, _school_id(session_user), period_year)
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


@dynamic_forms.post("/store")
def store(
    data: StoreDynamicForm,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        payload = data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data.dict()
        result = DynamicFormClass(db).store(payload, _school_id(session_user))
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": 400, "message": result.get("message", "Error al guardar"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "Creado"),
                "data": {
                    "id": result.get("id"),
                    "whatsapp": result.get("whatsapp"),
                },
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@dynamic_forms.put("/{id}")
def update(
    id: int,
    data: UpdateDynamicForm,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        payload = data.model_dump(exclude_unset=True, by_alias=True) if hasattr(data, "model_dump") else {}
        result = DynamicFormClass(db).update(id, payload, _school_id(session_user))
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Registro no encontrado"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Actualizado"),
                "data": {
                    "id": id,
                    "whatsapp": result.get("whatsapp"),
                },
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@dynamic_forms.delete("/{id}")
def delete(
    id: int,
    period_year: int = Query(..., ge=2000, le=2100, description="Año del período escolar"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        result = DynamicFormClass(db).delete(id, _school_id(session_user), period_year)
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
