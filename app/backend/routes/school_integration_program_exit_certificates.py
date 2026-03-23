from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from app.backend.classes.school_integration_program_exit_certificate_class import SchoolIntegrationProgramExitCertificateClass
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import (
    UserLogin,
    StoreSchoolIntegrationProgramExitCertificate,
    UpdateSchoolIntegrationProgramExitCertificate,
    SchoolIntegrationProgramExitCertificateList,
)
from sqlalchemy.orm import Session

school_integration_program_exit_certificates = APIRouter(
    prefix="/school_integration_program_exit_certificates",
    tags=["School Integration Program Exit Certificates"],
)


@school_integration_program_exit_certificates.post("/store")
async def store_school_integration_program_exit_certificate(
    data: StoreSchoolIntegrationProgramExitCertificate,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea un nuevo certificado de egreso del programa de integración escolar."""
    try:
        service = SchoolIntegrationProgramExitCertificateClass(db)
        result = service.store(data.dict())
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error guardando certificado"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "Certificado creado exitosamente"),
                "data": {"id": result.get("id")},
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error creando certificado: {str(e)}",
                "data": None,
            },
        )


@school_integration_program_exit_certificates.get("/list/{student_id}")
async def list_certificates_by_student(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista todos los certificados de un estudiante."""
    try:
        service = SchoolIntegrationProgramExitCertificateClass(db)
        data = service.get_all(student_id=student_id)
        if isinstance(data, dict) and data.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": data.get("message", "Error listando certificados"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Certificados encontrados" if data else "No hay certificados para este estudiante",
                "data": data,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error listando certificados: {str(e)}",
                "data": None,
            },
        )


@school_integration_program_exit_certificates.get("/student/{student_id}")
async def get_certificate_by_student(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene el último certificado por el ID del estudiante."""
    try:
        service = SchoolIntegrationProgramExitCertificateClass(db)
        result = service.get_by_student_id(student_id)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Certificado no encontrado para el estudiante"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Certificado encontrado",
                "data": result,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo certificado: {str(e)}",
                "data": None,
            },
        )


@school_integration_program_exit_certificates.get("/{id}")
async def get_certificate(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene un certificado por su ID."""
    try:
        service = SchoolIntegrationProgramExitCertificateClass(db)
        result = service.get(id)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Certificado no encontrado"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Certificado encontrado",
                "data": result,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo certificado: {str(e)}",
                "data": None,
            },
        )


@school_integration_program_exit_certificates.post("/")
async def list_certificates(
    filters: SchoolIntegrationProgramExitCertificateList = SchoolIntegrationProgramExitCertificateList(),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista certificados. Filtro opcional por student_id."""
    try:
        service = SchoolIntegrationProgramExitCertificateClass(db)
        data = service.get_all(student_id=filters.student_id)
        if isinstance(data, dict) and data.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": data.get("message", "Error listando certificados"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Certificados encontrados" if data else "No hay certificados registrados",
                "data": data,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error listando certificados: {str(e)}",
                "data": None,
            },
        )


@school_integration_program_exit_certificates.put("/{id}")
async def update_certificate(
    id: int,
    data: UpdateSchoolIntegrationProgramExitCertificate,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza un certificado existente."""
    try:
        service = SchoolIntegrationProgramExitCertificateClass(db)
        result = service.update(id, data.dict(exclude_unset=True))
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Error actualizando certificado"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Certificado actualizado exitosamente"),
                "data": {"id": result.get("id")},
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error actualizando certificado: {str(e)}",
                "data": None,
            },
        )


@school_integration_program_exit_certificates.delete("/{id}")
async def delete_certificate(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Elimina un certificado."""
    try:
        service = SchoolIntegrationProgramExitCertificateClass(db)
        result = service.delete(id)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Error eliminando certificado"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Certificado eliminado exitosamente"),
                "data": None,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error eliminando certificado: {str(e)}",
                "data": None,
            },
        )
