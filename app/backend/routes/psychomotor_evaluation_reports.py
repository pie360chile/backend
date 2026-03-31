from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StorePsychomotorEvaluationReport
from app.backend.classes.psychomotor_evaluation_report_class import PsychomotorEvaluationReportClass

psychomotor_evaluation_reports = APIRouter(
    prefix="/psychomotor_evaluation_reports",
    tags=["Informe de evaluación psicomotriz"],
)


@psychomotor_evaluation_reports.post("/store")
async def store_psychomotor_evaluation_report(
    data: StorePsychomotorEvaluationReport,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        payload = data.dict() if hasattr(data, "dict") else data.model_dump()
        service = PsychomotorEvaluationReportClass(db)
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


@psychomotor_evaluation_reports.get("/student/{student_id}")
async def get_psychomotor_evaluation_report_by_student(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        service = PsychomotorEvaluationReportClass(db)
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


@psychomotor_evaluation_reports.put("/{report_id}")
async def update_psychomotor_evaluation_report(
    report_id: int,
    data: StorePsychomotorEvaluationReport,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        payload = data.dict() if hasattr(data, "dict") else data.model_dump()
        service = PsychomotorEvaluationReportClass(db)
        result = service.update(report_id, payload)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Informe no encontrado.")},
            )
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": result.get("message", "OK")})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e)})
