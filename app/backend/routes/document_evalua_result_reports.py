from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin
from app.backend.classes.evalua_result_class import EvaluaResultClass

document_evalua_result_reports = APIRouter(
    prefix="/document_evalua_result_reports",
    tags=["Informes Resultado Prueba Evalua"],
)


@document_evalua_result_reports.get("/student/{student_id}")
async def get_document_evalua_by_student(
    student_id: int,
    document_catalog_id: int = Query(42, description="Id de fila en catálogo `documents` (típico: 42)."),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        svc = EvaluaResultClass(db)
        result = svc.get_by_student(student_id, document_catalog_id)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "OK",
                "data": result.get("data"),
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )
