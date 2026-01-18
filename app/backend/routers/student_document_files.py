from fastapi import APIRouter, status, UploadFile, File, Depends, Query
from fastapi.responses import JSONResponse
from app.backend.classes.student_document_file_class import FolderClass
from app.backend.classes.student_class import StudentClass
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin
from typing import Optional
from sqlalchemy.orm import Session
from pathlib import Path
import os
import uuid

student_document_files = APIRouter(
    prefix="/student-document-files",
    tags=["Student Document Files"]
)

@student_document_files.post("/upload/{student_id}/{document_id}")
async def upload_document_file(
    student_id: int,
    document_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Sube un archivo de documento para un estudiante y documento específico.
    Maneja el control de versiones automáticamente.
    """
    try:
        # Obtener el estudiante usando la clase
        student_service = StudentClass(db)
        student_result = student_service.get(student_id)
        
        if isinstance(student_result, dict) and (student_result.get("error") or student_result.get("status") == "error"):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": student_result.get("error") or student_result.get("message", "Estudiante no encontrado"),
                    "data": None
                }
            )

        # Obtener la extensión del archivo original
        file_extension = Path(file.filename).suffix.lower() if file.filename else ''
        
        # Generar nombre único para el archivo
        unique_id = uuid.uuid4().hex[:8]
        unique_filename = f"student_{student_id}_doc_{document_id}_{unique_id}{file_extension}"
        
        # Crear directorio si no existe
        upload_dir = Path("files/system/student_document_files")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / unique_filename
        
        # Guardar el archivo
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Guardar el registro en la base de datos usando el método store
        document_file_service = FolderClass(db)
        store_result = document_file_service.store(
            student_id=student_id,
            document_id=document_id,
            file_path=unique_filename
        )
        
        if isinstance(store_result, dict) and store_result.get("status") == "error":
            # Si hay error al guardar el registro, eliminar el archivo
            if file_path.exists():
                try:
                    os.unlink(file_path)
                except:
                    pass
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": store_result.get("message", "Error guardando registro del archivo de documento"),
                    "data": None
                }
            )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": "Archivo de documento subido exitosamente",
                "data": {
                    "id": store_result.get("id"),
                    "version_id": store_result.get("version_id"),
                    "student_id": student_id,
                    "document_id": document_id,
                    "filename": unique_filename,
                    "file_path": str(file_path),
                    "original_filename": file.filename
                }
            }
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error subiendo archivo: {str(e)}",
                "data": None
            }
        )

@student_document_files.get("/{id}")
async def get_document_file(
    id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene un archivo de documento por su ID.
    """
    try:
        document_file_service = FolderClass(db)
        result = document_file_service.get(id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Archivo de documento no encontrado"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Archivo de documento encontrado",
                "data": result
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo archivo de documento: {str(e)}",
                "data": None
            }
        )

@student_document_files.get("/list")
async def list_document_files(
    student_id: Optional[int] = Query(None),
    document_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Lista los archivos de documentos almacenados.
    Puede filtrarse por student_id y/o document_id.
    """
    try:
        document_file_service = FolderClass(db)
        data = document_file_service.get_all(student_id, document_id)

        if isinstance(data, dict) and data.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": data.get("message", "Error listando archivos de documentos"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Archivos de documentos encontrados" if data else "No hay archivos de documentos registrados",
                "data": data
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error listando archivos de documentos: {str(e)}",
                "data": None
            }
        )

@student_document_files.get("/student/{student_id}/document/{document_id}")
async def get_document_files_by_student_and_document(
    student_id: int,
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los archivos de documento para un estudiante y documento específico.
    Útil para ver el historial de versiones.
    """
    try:
        document_file_service = FolderClass(db)
        data = document_file_service.get_by_student_and_document(student_id, document_id)

        if isinstance(data, dict) and data.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": data.get("message", "Error obteniendo archivos de documentos"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Archivos de documentos encontrados" if data else "No hay archivos de documentos registrados",
                "data": data
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error obteniendo archivos de documentos: {str(e)}",
                "data": None
            }
        )


