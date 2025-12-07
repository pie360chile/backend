from fastapi import APIRouter, status, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse, FileResponse
from app.backend.classes.documents_class import DocumentsClass
from app.backend.classes.student_class import StudentClass
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import (
    UserLogin,
    CreateDocumentRequest,
    DocumentListRequest,
    UploadDocumentRequest
)
from sqlalchemy.orm import Session
from pathlib import Path
import tempfile
import os
from datetime import datetime
import uuid

documents = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

@documents.post("/create")
async def create_document(
    file: UploadFile = File(...),
    document_data: CreateDocumentRequest = Depends(CreateDocumentRequest.as_form)
):
    """
    Crea un documento procesado a partir de un PDF subido.
    Reemplaza [STUDENT_NAMES] con el nombre del estudiante proporcionado.
    """
    temp_file_path = None
    try:
        # Validar que el archivo sea PDF
        if not file.filename.endswith('.pdf'):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": 400,
                    "message": "El archivo debe ser un PDF",
                    "data": None
                }
            )
        
        # Guardar el archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Procesar el documento usando el método parent_authorization
        student_name = document_data.student_name
        document_type_id = document_data.document_type_id

        result = DocumentsClass.parent_authorization(
            original_file_path=temp_file_path,
            student_name=student_name
        )
        
        # Limpiar archivo temporal
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        
        if result["status"] == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result["message"],
                    "data": None
                }
            )
        
        # Devolver el archivo procesado para descarga
        response = FileResponse(
            path=result["file_path"],
            filename=result["filename"],
            media_type='application/pdf'
        )
        response.headers["X-Document-Type-Id"] = str(document_type_id)
        return response
        
    except Exception as e:
        # Limpiar archivo temporal en caso de error
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error general: {str(e)}",
                "data": None
            }
        )

@documents.post("/upload/{student_id}/{document_type_id}")
async def upload_document(
    student_id: int,
    document_type_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Sube un documento (PDF o imagen).
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
        
        student_data = student_result.get("student_data", {})
        student_identification_number = student_data.get("identification_number") or str(student_id)

        # Obtener el documento usando la clase
        document = DocumentsClass(db)
        document_result = document.get(document_type_id)
        
        if isinstance(document_result, dict) and document_result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": document_result.get("message", "Documento no encontrado"),
                    "data": None
                }
            )
        
        document_id = document_result.get("id")
        
        # Obtener la extensión del archivo original
        file_extension = Path(file.filename).suffix.lower() if file.filename else ''
        
        # Limpiar el RUT para que sea válido en nombre de archivo (remover caracteres especiales)
        clean_rut = student_identification_number.replace('.', '').replace('-', '')
        
        # Generar nombre del archivo: document_{identification_number}_{documents.id}
        unique_filename = f"document_{clean_rut}_{document_id}{file_extension}"
        
        # Crear directorio si no existe
        upload_dir = Path("files/system/students")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / unique_filename
        
        # Guardar el archivo
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Guardar el registro en la tabla correspondiente usando el método store
        store_result = document.store(
            student_id=student_id,
            document_type_id=document_type_id,
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
                    "message": store_result.get("message", "Error guardando registro del documento"),
                    "data": None
                }
            )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": "Documento subido exitosamente",
                "data": {
                    "id": store_result.get("document_id"),
                    "version_id": store_result.get("version_id"),
                    "student_id": student_id,
                    "document_type_id": document_type_id,
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

@documents.post("/list")
async def list_documents(
    filters: DocumentListRequest,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lista los documentos configurados, devolviendo solo document_type_id y document.
    """
    try:
        documents = DocumentsClass(db)
        data = documents.get_all(filters.document_type_id, filters.career_type_id)

        if isinstance(data, dict) and data.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": data.get("message", "Error listando documentos"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Documentos encontrados" if data else "No hay documentos registrados",
                "data": data
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error listando documentos: {str(e)}",
                "data": None
            }
        )

@documents.get("/download/{filename}")
async def download_document(
    filename: str
):
    try:
        file_path = Path("files/original_student_files") / filename
        
        if not file_path.exists():
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": "Archivo no encontrado",
                    "data": None
                }
            )
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='application/pdf'
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error descargando archivo: {str(e)}",
                "data": None
            }
        )

