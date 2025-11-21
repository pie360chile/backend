from fastapi import APIRouter, status, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse, FileResponse
from app.backend.classes.documents_class import DocumentsClass
from app.backend.classes.files_class import FileClass
from app.backend.db.database import get_db
from app.backend.db.models import StudentDocumentModel
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin
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
    student_name: str = Form(...)
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
        result = DocumentsClass().parent_authorization(
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
        return FileResponse(
            path=result["file_path"],
            filename=result["filename"],
            media_type='application/pdf'
        )
        
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

@documents.post("/upload-birth-certificate")
async def upload_birth_certificate(
    file: UploadFile = File(...)
):
    """
    Sube un certificado de nacimiento (solo archivo PDF).
    """
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
        
        # Crear directorio si no existe
        upload_dir = Path("files/system/students")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generar nombre único para el archivo
        import uuid
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"birth_cert_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
        file_path = upload_dir / unique_filename
        
        # Guardar el archivo
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": "Certificado de nacimiento subido exitosamente",
                "data": {
                    "filename": unique_filename,
                    "file_path": str(file_path),
                    "original_filename": file.filename
                }
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error subiendo archivo: {str(e)}",
                "data": None
            }
        )

@documents.post("/upload")
async def upload_document(
    student_id: int = Form(...),
    file: UploadFile = File(...),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Sube un certificado de nacimiento asociado a un estudiante.
    """
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
        
        # Generar nombre único para el archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"birth_cert_student_{student_id}_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
        remote_path = f"system/students/{unique_filename}"
        
        # Leer el contenido del archivo
        content = await file.read()
        
        # Usar FileClass para guardar el archivo
        file_class = FileClass(db)
        file_class.temporal_upload(content, remote_path)
        
        # Obtener la URL del archivo
        file_url = file_class.get(remote_path)
        
        # Buscar si ya existe un documento para este estudiante
        existing_doc = db.query(StudentDocumentModel).filter(
            StudentDocumentModel.student_id == student_id
        ).first()
        
        if existing_doc:
            # Actualizar el registro existente
            existing_doc.birth_certificate = file_url
            existing_doc.updated_date = datetime.now()
            db.commit()
            db.refresh(existing_doc)
            document_id = existing_doc.id
        else:
            # Crear nuevo registro
            new_doc = StudentDocumentModel(
                student_id=student_id,
                birth_certificate=file_url,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )
            db.add(new_doc)
            db.commit()
            db.refresh(new_doc)
            document_id = new_doc.id
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": "Documento subido exitosamente",
                "data": {
                    "id": document_id,
                    "student_id": student_id,
                    "filename": unique_filename,
                    "file_url": file_url,
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

