"""Plantillas de pruebas informales (reutilizables por colegio)."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.informal_test_template_class import InformalTestTemplateClass
from app.backend.db.database import get_db
from app.backend.schemas import (
    StoreInformalTestTemplate,
    SubmitInformalTestTemplateAnswers,
    UpdateInformalTestTemplate,
    UserLogin,
)

informal_test_templates = APIRouter(
    prefix="/informal_test_templates",
    tags=["Informal Test Templates"],
)


def _school_id(user: UserLogin) -> int:
    sid = int(user.school_id or 0)
    return sid


@informal_test_templates.get("")
def get_list(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        sid = _school_id(session_user)
        data = InformalTestTemplateClass(db).get_all(sid)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": "OK", "data": data})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e), "data": []})


@informal_test_templates.get("/{id}")
def get_by_id(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        sid = _school_id(session_user)
        result = InformalTestTemplateClass(db).get_by_id(id, sid)
        if result.get("status") == "error":
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"status": 404, "message": result.get("message"), "data": None})
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": "OK", "data": result.get("data")})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e), "data": None})


@informal_test_templates.get("/submissions/student/{student_id}")
def get_submissions_by_student(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        sid = _school_id(session_user)
        data = InformalTestTemplateClass(db).get_student_submissions(sid, student_id)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": "OK", "data": data})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e), "data": []})


@informal_test_templates.get("/{id}/submissions/student/{student_id}/latest")
def get_latest_submission_by_template_student(
    id: int,
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        sid = _school_id(session_user)
        result = InformalTestTemplateClass(db).get_latest_submission_answers(sid, id, student_id)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": "OK", "data": result.get("data")})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e), "data": None})


@informal_test_templates.post("/store")
def store(
    body: StoreInformalTestTemplate,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        sid = _school_id(session_user)
        payload = body.model_dump() if hasattr(body, "model_dump") else body.dict()
        payload["professional_id"] = int(
            getattr(session_user, "id", 0)
            or getattr(session_user, "customer_id", 0)
            or 0
        )
        payload["session_course_id"] = int(getattr(session_user, "course_id", 0) or 0) or None
        payload["session_period_year"] = getattr(session_user, "period_year", None)
        result = InformalTestTemplateClass(db).store(payload, sid)
        if result.get("status") == "error":
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"status": 400, "message": result.get("message"), "data": None})
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": 201, "message": result.get("message", "Plantilla creada."), "data": {"id": result.get("id")}},
        )
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e), "data": None})


@informal_test_templates.put("/{id}")
def update(
    id: int,
    body: UpdateInformalTestTemplate,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        sid = _school_id(session_user)
        payload = body.model_dump(exclude_unset=True) if hasattr(body, "model_dump") else body.dict()
        result = InformalTestTemplateClass(db).update(id, payload, sid)
        if result.get("status") == "error":
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"status": 400, "message": result.get("message"), "data": None})
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": result.get("message"), "data": {"id": id}})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e), "data": None})


@informal_test_templates.delete("/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        sid = _school_id(session_user)
        result = InformalTestTemplateClass(db).delete(id, sid)
        if result.get("status") == "error":
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"status": 404, "message": result.get("message"), "data": None})
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": result.get("message"), "data": None})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e), "data": None})


@informal_test_templates.post("/{id}/submissions")
def submit_answers(
    id: int,
    body: SubmitInformalTestTemplateAnswers,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        sid = _school_id(session_user)
        payload = body.model_dump() if hasattr(body, "model_dump") else body.dict()
        professional_id = int(
            getattr(session_user, "id", 0)
            or getattr(session_user, "customer_id", 0)
            or 0
        )
        result = InformalTestTemplateClass(db).submit_answers(
            template_id=id,
            school_id=sid,
            student_id=int(payload.get("student_id")),
            professional_id=professional_id,
            answers=payload.get("answers") or {},
            session_course_id=int(getattr(session_user, "course_id", 0) or 0) or None,
            session_period_year=getattr(session_user, "period_year", None),
        )
        if result.get("status") == "error":
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"status": 400, "message": result.get("message"), "data": None})
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": 201, "message": result.get("message", "Respuestas guardadas."), "data": {"id": result.get("id")}},
        )
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e), "data": None})
