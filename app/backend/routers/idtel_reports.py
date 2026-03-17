from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StoreIdtelReport
from app.backend.classes.idtel_report_class import IdtelReportClass

idtel_reports = APIRouter(
    prefix="/idtel_reports",
    tags=["IDTEL Reports"],
)

@idtel_reports.post("/store")
async def store_idtel_report(
    data: StoreIdtelReport,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea un nuevo informe IDTEL (Documento 9)."""
    try:
        payload = data.dict()
        service = IdtelReportClass(db)
        result = service.store(payload)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error guardando informe IDTEL"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": 201, "message": result.get("message", "Informe IDTEL creado."), "data": {"id": result.get("id")}},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@idtel_reports.get("/student/{student_id}")
async def get_idtel_report_by_student(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene el último informe IDTEL por estudiante."""
    try:
        service = IdtelReportClass(db)
        result = service.get_by_student_id(student_id)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Informe IDTEL no encontrado."), "data": None},
            )
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": "OK", "data": result})
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@idtel_reports.put("/{id}")
async def update_idtel_report(
    id: int,
    data: StoreIdtelReport,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza un informe IDTEL."""
    try:
        payload = data.dict()
        service = IdtelReportClass(db)
        result = service.update(id, payload)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Informe IDTEL no encontrado.")},
            )
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": result.get("message", "OK")})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e)})
