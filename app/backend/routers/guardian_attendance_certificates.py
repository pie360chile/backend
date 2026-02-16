from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from app.backend.classes.guardian_attendance_certificate_class import GuardianAttendanceCertificateClass
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StoreGuardianAttendanceCertificate, UpdateGuardianAttendanceCertificate
from typing import Optional
from sqlalchemy.orm import Session

guardian_attendance_certificates = APIRouter(
    prefix="/guardian_attendance_certificates",
    tags=["Guardian Attendance Certificates (Document 25)"],
)


@guardian_attendance_certificates.post("/store")
async def store_guardian_attendance_certificate(
    data: StoreGuardianAttendanceCertificate,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea un nuevo certificado de asistencia del apoderado (Documento 25 - Ley TEA)."""
    try:
        service = GuardianAttendanceCertificateClass(db)
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        result = service.store(payload)

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


@guardian_attendance_certificates.get("/list/all")
async def list_guardian_attendance_certificates(
    student_id: Optional[int] = None,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista certificados de asistencia del apoderado, opcionalmente filtrados por student_id."""
    try:
        service = GuardianAttendanceCertificateClass(db)
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
                "message": "Certificados encontrados" if data else "No hay certificados",
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


@guardian_attendance_certificates.get("/by-student/{student_id}")
async def get_guardian_attendance_certificate_by_student(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene el certificado más reciente por student_id (Documento 25)."""
    try:
        service = GuardianAttendanceCertificateClass(db)
        result = service.get_by_student_id(student_id)

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


@guardian_attendance_certificates.get("/by-id/{id}")
async def get_guardian_attendance_certificate(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene un certificado por ID."""
    try:
        service = GuardianAttendanceCertificateClass(db)
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


@guardian_attendance_certificates.put("/{id}")
async def update_guardian_attendance_certificate(
    id: int,
    data: UpdateGuardianAttendanceCertificate,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza un certificado existente."""
    try:
        service = GuardianAttendanceCertificateClass(db)
        payload = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else data.dict(exclude_unset=True)
        result = service.update(id, payload)

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


@guardian_attendance_certificates.delete("/{id}")
async def delete_guardian_attendance_certificate(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Elimina un certificado."""
    try:
        service = GuardianAttendanceCertificateClass(db)
        result = service.delete(id)

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
