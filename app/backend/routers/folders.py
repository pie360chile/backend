from fastapi import APIRouter, status, Depends, Query, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from app.backend.classes.student_document_file_class import FolderClass
from app.backend.classes.student_class import StudentClass
from app.backend.classes.files_class import FileClass
from app.backend.db.database import get_db
from typing import Optional
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime
import uuid
import mimetypes

folders = APIRouter(
    prefix="/folders",
    tags=["Folders"]
)

@folders.get("/checkDocumentExistence/{student_id}/{document_type_id}")
async def checkDocumentExistence(
    student_id: int,
    document_type_id: int,
    db: Session = Depends(get_db)
):
    """
    Verifica si un estudiante ya tiene documentos de un tipo específico.
    Busca directamente en la tabla correspondiente según el document_type_id:
    - document_type_id = 1: busca en birth_certificate_documents
    - document_type_id = 4: busca en health_evaluations
    - Otros: busca en folders filtrando por document_type_id
    Retorna información sobre la existencia del documento filtrado por student_id y document_type_id.
    """
    try:
        folder_service = FolderClass(db)
        result = folder_service.check_document_existence(student_id, document_type_id)

        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error verificando existencia del documento"),
                    "exists": False,
                    "total": 0,
                    "data": []
                }
            )

        # Asegurar que data sea un array siempre
        data = result.get("data")
        if data is None:
            data = []
        elif not isinstance(data, list):
            data = [data] if data else []
        
        # Asegurar que missing sea un array siempre
        missing = result.get("missing")
        if missing is None:
            missing = []
        elif not isinstance(missing, list):
            missing = [missing] if missing else []
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message"),
                "exists": result.get("exists"),
                "total": result.get("total", 0),
                "total_missing": result.get("total_missing", 0),
                "data": data,
                "missing": missing
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": f"Error verificando existencia del documento: {str(e)}",
                    "exists": False,
                    "total": 0,
                    "data": []
                }
        )

@folders.post("/upload/{student_id}/{document_id}")
async def upload_document(
    student_id: int,
    document_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Sube un archivo de documento para un estudiante y documento específico en la tabla folders.
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

        # Obtener document_type_id desde document_id (solo documentos no eliminados)
        from app.backend.db.models import DocumentModel
        document_info = db.query(DocumentModel).filter(
            DocumentModel.id == document_id,
            DocumentModel.deleted_date.is_(None)
        ).first()
        
        if not document_info:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": f"Documento con id {document_id} no encontrado",
                    "data": None
                }
            )
        
        document_type_id = document_info.document_type_id
        
        # Obtener la extensión del archivo original
        file_extension = Path(file.filename).suffix.lower() if file.filename else ''
        
        # Generar fecha y hora en formato YYYYMMDDHHMMSS
        date_hour = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Generar nombre del archivo: {student_id}_{document_id}_{document_type_id}_{date_hour}
        unique_filename = f"{student_id}_{document_id}_{document_type_id}_{date_hour}{file_extension}"
        
        # Usar FileClass para subir el archivo
        file_service = FileClass(db)
        remote_path = f"system/folders/{unique_filename}"
        
        try:
            # Subir el archivo usando FileClass
            file_service.upload(file, remote_path)
        except Exception as upload_error:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": f"Error subiendo archivo: {str(upload_error)}",
                    "data": None
                }
            )
        
        # Guardar el registro en la base de datos usando el método store
        folder_service = FolderClass(db)
        store_result = folder_service.store(
            student_id=student_id,
            document_id=document_id,
            file_path=unique_filename
        )
        
        if isinstance(store_result, dict) and store_result.get("status") == "error":
            # Si hay error al guardar el registro, eliminar el archivo
            try:
                file_service.delete(remote_path)
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
                    "file_path": remote_path,
                    "file_url": file_service.get(remote_path),
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

@folders.get("/list/{student_id}/{document_id}")
async def list_folders(
    student_id: int,
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Lista los registros de folders filtrados por student_id y document_id.
    Retorna todos los registros ordenados por version_id descendente.
    """
    try:
        folder_service = FolderClass(db)
        result = folder_service.get_by_student_and_document(student_id, document_id)
        
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error listando documentos"),
                    "data": []
                }
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": f"Se encontraron {len(result)} documento(s)",
                "total": len(result),
                "data": result
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error listando documentos: {str(e)}",
                "data": []
            }
        )

@folders.get("/download/{id}")
async def download_document(
    id: int,
    db: Session = Depends(get_db)
):
    """
    Descarga un documento de folders por su ID.
    El archivo debe estar en files/system/students/
    """
    try:
        folder_service = FolderClass(db)
        result = folder_service.get(id)
        
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Documento no encontrado"),
                    "data": None
                }
            )
        
        filename = result.get("file")
        if not filename:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": "El registro no tiene archivo asociado",
                    "data": None
                }
            )
        
        # Asegurar que el filename solo contenga el nombre del archivo, sin rutas
        filename = Path(filename).name
        
        # Ruta del archivo en files/system/students
        file_path = Path("files/system/students") / filename
        
        if not file_path.exists():
            # Intentar también con el nombre completo tal como está en la BD
            file_path_alt = Path("files/system/students") / result.get("file")
            if file_path_alt.exists():
                file_path = file_path_alt
            else:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": f"Archivo no encontrado: {filename}. Buscando en: {file_path}",
                        "data": None
                    }
                )
        
        # Determinar el tipo MIME basado en la extensión
        media_type, _ = mimetypes.guess_type(str(file_path))
        if not media_type:
            # Por defecto, usar application/octet-stream si no se puede determinar
            media_type = "application/octet-stream"
        
        # Usar el nombre original del archivo para la descarga
        download_filename = filename
        
        return FileResponse(
            path=str(file_path),
            filename=download_filename,
            media_type=media_type
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
