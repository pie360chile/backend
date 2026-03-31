from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StoreDocument41PsychomotorReport
from app.backend.classes.document_41_report_class import Document41ReportClass

document_41_reports = APIRouter(
    prefix="/document_41_reports",
    tags=["Document 41 – Evaluación psicomotriz"],
)


@document_41_reports.post("/store")
async def store_document_41(
    data: StoreDocument41PsychomotorReport,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        payload = data.dict() if hasattr(data, "dict") else data.model_dump()
        service = Document41ReportClass(db)
        result = service.store(payload)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error al guardar"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": 201, "message": result.get("message", "Informe creado."), "data": {"id": result.get("id")}},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@document_41_reports.get("/student/{student_id}")
async def get_document_41_by_student(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        service = Document41ReportClass(db)
        result = service.get_by_student_id(student_id)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Informe no encontrado."), "data": None},
            )
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": "OK", "data": result})
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@document_41_reports.put("/{id}")
async def update_document_41(
    id: int,
    data: StoreDocument41PsychomotorReport,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        payload = data.dict() if hasattr(data, "dict") else data.model_dump()
        service = Document41ReportClass(db)
        result = service.update(id, payload)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Informe no encontrado.")},
            )
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": result.get("message", "OK")})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e)})
