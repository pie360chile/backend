from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from app.backend.classes.family_report_class import FamilyReportClass
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StoreFamilyReport, UpdateFamilyReport
from typing import Optional
from sqlalchemy.orm import Session

family_reports = APIRouter(
    prefix="/family_reports",
    tags=["Family Reports"]
)

@family_reports.post("/store")
async def store_family_report(
    data: StoreFamilyReport,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Crea un nuevo Informe Familiar (Documento 7)."""
    try:
        service = FamilyReportClass(db)
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        result = service.store(payload)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error guardando informe familiar"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "Informe familiar creado exitosamente"),
                "data": {"id": result.get("id")}
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error creando informe familiar: {str(e)}",
                "data": None
            }
        )


@family_reports.get("/by-id/{student_id}")
async def get_family_report_by_id(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtiene el informe familiar más reciente por ID del estudiante."""
    try:
        service = FamilyReportClass(db)
        result = service.get_by_student_id(student_id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Informe familiar no encontrado"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Informe familiar encontrado",
                "data": result
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo informe familiar: {str(e)}",
                "data": None
            }
        )


@family_reports.put("/{id}")
async def update_family_report(
    id: int,
    data: UpdateFamilyReport,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Actualiza un informe familiar existente."""
    try:
        service = FamilyReportClass(db)
        payload = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else data.dict(exclude_unset=True)
        result = service.update(id, payload)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Error actualizando informe familiar"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Informe familiar actualizado exitosamente"),
                "data": {"id": result.get("id")}
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error actualizando informe familiar: {str(e)}",
                "data": None
            }
        )


@family_reports.get("/{student_id}")
async def get_family_report_by_student(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtiene el informe familiar más reciente por student_id."""
    try:
        service = FamilyReportClass(db)
        result = service.get_by_student_id(student_id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Informe familiar no encontrado"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Informe familiar encontrado",
                "data": result
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo informe familiar: {str(e)}",
                "data": None
            }
        )


@family_reports.get("/list/all")
async def list_family_reports(
    student_id: Optional[int] = None,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lista informes familiares, opcionalmente filtrados por student_id."""
    try:
        service = FamilyReportClass(db)
        data = service.get_all(student_id=student_id)

        if isinstance(data, dict) and data.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": data.get("message", "Error listando informes familiares"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Informes familiares encontrados" if data else "No hay informes familiares",
                "data": data
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error listando informes familiares: {str(e)}",
                "data": None
            }
        )


@family_reports.delete("/{id}")
async def delete_family_report(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Elimina un informe familiar."""
    try:
        service = FamilyReportClass(db)
        result = service.delete(id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Informe familiar no encontrado"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Informe familiar eliminado exitosamente"),
                "data": None
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error eliminando informe familiar: {str(e)}",
                "data": None
            }
        )
