from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from app.backend.classes.fonoaudiological_report_class import FonoaudiologicalReportClass
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StoreFonoaudiologicalReport, UpdateFonoaudiologicalReport, FonoaudiologicalReportList
from sqlalchemy.orm import Session

fonoaudiological_reports = APIRouter(
    prefix="/fonoaudiological_reports",
    tags=["Fonoaudiological Reports"]
)

@fonoaudiological_reports.post("/store")
async def store_fonoaudiological_report(
    data: StoreFonoaudiologicalReport,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Crea un nuevo informe fonoaudiológico (Documento 8)."""
    try:
        service = FonoaudiologicalReportClass(db)
        result = service.store(data.dict())
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={
                "status": 500, "message": result.get("message", "Error guardando informe fonoaudiológico"), "data": None
            })
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={
            "status": 201, "message": result.get("message", "Informe fonoaudiológico creado exitosamente"),
            "data": {"id": result.get("id")}
        })
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={
            "status": 500, "message": f"Error creando informe fonoaudiológico: {str(e)}", "data": None
        })

@fonoaudiological_reports.get("/list/{student_id}")
async def list_fonoaudiological_reports_by_student(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lista todos los informes fonoaudiológicos de un estudiante."""
    try:
        service = FonoaudiologicalReportClass(db)
        data = service.get_all(student_id=student_id)
        if isinstance(data, dict) and data.get("status") == "error":
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={
                "status": 500, "message": data.get("message", "Error listando informes"), "data": None
            })
        return JSONResponse(status_code=status.HTTP_200_OK, content={
            "status": 200,
            "message": "Informes fonoaudiológicos encontrados" if data else "No hay informes para este estudiante",
            "data": data
        })
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={
            "status": 500, "message": f"Error listando informes fonoaudiológicos: {str(e)}", "data": None
        })

@fonoaudiological_reports.get("/student/{student_id}")
async def get_fonoaudiological_report_by_student(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtiene el último informe fonoaudiológico por el ID del estudiante."""
    try:
        service = FonoaudiologicalReportClass(db)
        result = service.get_by_student_id(student_id)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={
                "status": 404, "message": result.get("message", "Informe fonoaudiológico no encontrado para el estudiante"), "data": None
            })
        return JSONResponse(status_code=status.HTTP_200_OK, content={
            "status": 200, "message": "Informe fonoaudiológico encontrado", "data": result
        })
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={
            "status": 500, "message": f"Error obteniendo informe fonoaudiológico: {str(e)}", "data": None
        })

@fonoaudiological_reports.get("/{id}")
async def get_fonoaudiological_report(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtiene un informe fonoaudiológico por su ID."""
    try:
        service = FonoaudiologicalReportClass(db)
        result = service.get(id)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={
                "status": 404, "message": result.get("message", "Informe fonoaudiológico no encontrado"), "data": None
            })
        return JSONResponse(status_code=status.HTTP_200_OK, content={
            "status": 200, "message": "Informe fonoaudiológico encontrado", "data": result
        })
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={
            "status": 500, "message": f"Error obteniendo informe fonoaudiológico: {str(e)}", "data": None
        })

@fonoaudiological_reports.post("/")
async def list_fonoaudiological_reports(
    filters: FonoaudiologicalReportList = FonoaudiologicalReportList(),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lista informes fonoaudiológicos. Filtro opcional por student_id."""
    try:
        service = FonoaudiologicalReportClass(db)
        data = service.get_all(student_id=filters.student_id)
        if isinstance(data, dict) and data.get("status") == "error":
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={
                "status": 500, "message": data.get("message", "Error listando informes"), "data": None
            })
        return JSONResponse(status_code=status.HTTP_200_OK, content={
            "status": 200,
            "message": "Informes fonoaudiológicos encontrados" if data else "No hay informes registrados",
            "data": data
        })
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={
            "status": 500, "message": f"Error listando informes fonoaudiológicos: {str(e)}", "data": None
        })

@fonoaudiological_reports.put("/{id}")
async def update_fonoaudiological_report(
    id: int,
    data: UpdateFonoaudiologicalReport,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Actualiza un informe fonoaudiológico existente."""
    try:
        service = FonoaudiologicalReportClass(db)
        result = service.update(id, data.dict(exclude_unset=True))
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={
                "status": 404, "message": result.get("message", "Error actualizando informe"), "data": None
            })
        return JSONResponse(status_code=status.HTTP_200_OK, content={
            "status": 200, "message": result.get("message", "Informe actualizado exitosamente"),
            "data": {"id": result.get("id")}
        })
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={
            "status": 500, "message": f"Error actualizando informe fonoaudiológico: {str(e)}", "data": None
        })

@fonoaudiological_reports.delete("/{id}")
async def delete_fonoaudiological_report(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Elimina lógicamente un informe fonoaudiológico (soft delete)."""
    try:
        service = FonoaudiologicalReportClass(db)
        result = service.delete(id)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={
                "status": 404, "message": result.get("message", "Error eliminando informe"), "data": None
            })
        return JSONResponse(status_code=status.HTTP_200_OK, content={
            "status": 200, "message": result.get("message", "Informe eliminado exitosamente"), "data": None
        })
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={
            "status": 500, "message": f"Error eliminando informe fonoaudiológico: {str(e)}", "data": None
        })
