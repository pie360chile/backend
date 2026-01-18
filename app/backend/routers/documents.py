from fastapi import APIRouter, status, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse, FileResponse
from app.backend.classes.documents_class import DocumentsClass
from app.backend.classes.student_class import StudentClass
from app.backend.classes.health_evaluation_class import HealthEvaluationClass
from app.backend.db.database import get_db
from app.backend.db.models import FolderModel
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

@documents.post("/upload/{student_id}/{document_id}")
async def upload_document(
    student_id: int,
    document_id: int,
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

        # Obtener el documento por document_id para obtener su document_type_id
        from app.backend.db.models import DocumentModel
        document = db.query(DocumentModel).filter(
            DocumentModel.id == document_id
        ).first()
        
        if not document:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": f"No se encontró documento con document_id {document_id}",
                    "data": None
                }
            )
        
        # Obtener document_type_id del documento
        document_type_id = document.document_type_id
        
        # Obtener la extensión del archivo original
        file_extension = Path(file.filename).suffix.lower() if file.filename else ''
        
        # Generar fecha y hora en formato YYYYMMDDHHMMSS
        date_hour = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Generar nombre del archivo: {student_id}_{document_id}_{document_type_id}_{date_hour}
        unique_filename = f"{student_id}_{document_id}_{document_type_id}_{date_hour}{file_extension}"
        
        # Crear directorio si no existe
        upload_dir = Path("files/system/students")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / unique_filename
        
        # Guardar el archivo
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Guardar directamente en folders con el document_id correcto (no usar store que busca por document_type_id)
        # Buscar la última versión para este estudiante y documento
        last_version = db.query(FolderModel).filter(
            FolderModel.student_id == student_id,
            FolderModel.document_id == document_id
        ).order_by(FolderModel.version_id.desc()).first()
        
        # Determinar el nuevo version_id
        if last_version:
            new_version_id = last_version.version_id + 1
        else:
            new_version_id = 1
        
        # Crear el nuevo registro en folders
        new_folder = FolderModel(
            student_id=student_id,
            document_id=document_id,  # Usar el document_id correcto (2 en este caso)
            version_id=new_version_id,
            detail_id=None,
            file=unique_filename,
            added_date=datetime.now(),
            updated_date=datetime.now()
        )
        
        db.add(new_folder)
        db.commit()
        db.refresh(new_folder)
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": "Documento subido exitosamente",
                "data": {
                    "id": new_folder.id,
                    "document_id": document_id,
                    "version_id": new_version_id,
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

@documents.get("/generate/{student_id}/{document_id}")
async def generate_document(
    student_id: int,
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Genera un documento para un estudiante específico.
    Cuando document_id = 4, genera el documento de evaluación de salud desde health_evaluations.
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
        
        # Obtener el documento usando la clase
        document = DocumentsClass(db)
        document_result = document.get(document_id)
        
        if isinstance(document_result, dict) and document_result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": document_result.get("message", "Documento no encontrado"),
                    "data": None
                }
            )
        
        # Si document_id = 4, generar documento de evaluación de salud
        if document_id == 4:
            # Buscar la evaluación de salud más reciente para este estudiante
            # Primero intentar obtener desde folders usando detail_id
            folder_record = db.query(FolderModel).filter(
                FolderModel.student_id == student_id,
                FolderModel.document_id == 4
            ).order_by(FolderModel.id.desc()).first()
            
            evaluation_id = None
            if folder_record and folder_record.detail_id:
                evaluation_id = folder_record.detail_id
            else:
                # Si no hay folder, buscar la última evaluación directamente
                health_eval_service = HealthEvaluationClass(db)
                evaluations = health_eval_service.get_all(student_id=student_id)
                if evaluations and len(evaluations) > 0:
                    evaluation_id = evaluations[0].get("id") if isinstance(evaluations[0], dict) else None
            
            if not evaluation_id:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": "No se encontró evaluación de salud para este estudiante",
                        "data": None
                    }
                )
            
            # Obtener los datos de la evaluación
            health_eval_service = HealthEvaluationClass(db)
            evaluation_data = health_eval_service.get(evaluation_id)
            
            if isinstance(evaluation_data, dict) and evaluation_data.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": evaluation_data.get("message", "Evaluación de salud no encontrada"),
                        "data": None
                    }
                )
            
            # Ruta del template - usar health_evaluation.pdf
            template_path = Path("files/original_student_files") / "health_evaluation.pdf"
            
            if not template_path.exists():
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": "Template de evaluación de salud no encontrado. Buscando: health_evaluation.pdf",
                        "data": None
                    }
                )
            
            # Obtener datos adicionales de las tablas relacionadas
            from app.backend.db.models import GenderModel, NationalityModel, ProfessionalModel
            
            # Obtener género
            gender_name = ""
            if evaluation_data.get("gender_id"):
                gender = db.query(GenderModel).filter(GenderModel.id == evaluation_data.get("gender_id")).first()
                if gender:
                    gender_name = gender.gender or ""
            
            # Obtener nacionalidad
            nationality_name = ""
            if evaluation_data.get("nationality_id"):
                nationality = db.query(NationalityModel).filter(NationalityModel.id == evaluation_data.get("nationality_id")).first()
                if nationality:
                    nationality_name = nationality.nationality or ""
            
            # Obtener datos del profesional
            professional_fullname = ""
            if evaluation_data.get("profesional_id"):
                professional = db.query(ProfessionalModel).filter(ProfessionalModel.id == evaluation_data.get("profesional_id")).first()
                if professional:
                    professional_fullname = f"{professional.names or ''} {professional.lastnames or ''}".strip()
            
            # Agregar datos adicionales al evaluation_data
            evaluation_data["gender_name"] = gender_name
            evaluation_data["nationality_name"] = nationality_name
            evaluation_data["professional_fullname"] = professional_fullname
            
            # Generar el documento PDF
            result = DocumentsClass.generate_health_evaluation_pdf(
                template_path=str(template_path),
                evaluation_data=evaluation_data,
                db=db,
                output_directory="files/system/students"
            )
            
            if result["status"] == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", "Error generando documento"),
                        "data": None
                    }
                )
            
            # Guardar el documento generado en folders con document_id = 4
            try:
                generated_file = Path(result["file_path"])
                
                if generated_file.exists():
                    # Generar fecha y hora en formato YYYYMMDDHHMMSS
                    date_hour = datetime.now().strftime("%Y%m%d%H%M%S")
                    
                    # Obtener el document_type_id del documento (document_id = 4)
                    document_data = document_result if isinstance(document_result, dict) else {}
                    document_type_id = document_data.get("document_type_id")
                    
                    # Generar nombre del archivo: {student_id}_{document_id}_{document_type_id}_{date_hour}
                    file_extension = generated_file.suffix
                    health_eval_document_id = 4
                    unique_filename = f"{student_id}_{health_eval_document_id}_{document_type_id}_{date_hour}{file_extension}"
                    
                    # Renombrar el archivo generado al nombre único
                    system_file_path = Path("files/system/students") / unique_filename
                    system_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Mover/renombrar el archivo
                    from shutil import move
                    move(generated_file, system_file_path)
                    
                    # Actualizar el resultado con la nueva ruta
                    result["file_path"] = str(system_file_path)
                    result["filename"] = unique_filename
                    
                    # Buscar la última versión para este estudiante y documento (document_id = 4)
                    last_version = db.query(FolderModel).filter(
                        FolderModel.student_id == student_id,
                        FolderModel.document_id == health_eval_document_id
                    ).order_by(FolderModel.version_id.desc()).first()
                    
                    # Determinar el nuevo version_id
                    if last_version:
                        new_version_id = last_version.version_id + 1
                    else:
                        new_version_id = 1
                    
                    # Crear el nuevo registro en folders con document_id = 4
                    new_folder = FolderModel(
                        student_id=student_id,
                        document_id=health_eval_document_id,  # document_id = 4 para health_evaluation
                        version_id=new_version_id,
                        detail_id=evaluation_id,  # detail_id es el ID de la evaluación de salud
                        file=unique_filename,
                        added_date=datetime.now(),
                        updated_date=datetime.now()
                    )
                    
                    db.add(new_folder)
                    db.commit()
                    db.refresh(new_folder)
            except Exception as e:
                # Si falla el guardado en folders, continuar de todos modos
                print(f"Error guardando health_evaluation en folders: {str(e)}")
            
            # Retornar el archivo PDF generado
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type='application/pdf'
            )
        
        # Obtener datos del estudiante
        student_data = student_result.get("student_data", {}) if isinstance(student_result, dict) else {}
        student_name = student_data.get("full_name") or student_data.get("names") or f"Estudiante {student_id}"
        
        # Lógica específica por document_id
        # Si document_id = 2, usar parent_authorization
        if document_id == 2:
            # Buscar template PDF de parent_authorization
            possible_template_names = [
                "parent_authorization.pdf",
                "autorizacion_padres.pdf",
                "autorizacion.pdf"
            ]
            
            template_path = None
            for template_name in possible_template_names:
                test_path = Path("files/original_student_files") / template_name
                if test_path.exists():
                    template_path = test_path
                    break
            
            if not template_path:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": f"Template de autorización de padres no encontrado. Buscando: {', '.join(possible_template_names)}",
                        "data": None
                    }
                )
            
            # Obtener datos adicionales del estudiante y guardián
            from app.backend.classes.student_guardian_class import StudentGuardianClass
            from app.backend.db.models import FamilyMemberModel, CourseModel, SchoolModel, StudentAcademicInfoModel, CommuneModel
            
            # Obtener nombre completo del estudiante
            student_data = student_result.get("student_data", {}) if isinstance(student_result, dict) else {}
            personal_data = student_data.get("personal_data", {})
            
            # Construir nombre completo desde personal_data
            names = personal_data.get("names", "") or ""
            father_lastname = personal_data.get("father_lastname", "") or ""
            mother_lastname = personal_data.get("mother_lastname", "") or ""
            student_fullname = f"{names} {father_lastname} {mother_lastname}".strip()
            
            # Obtener curso y escuela
            course_school_location = ""
            academic_info = student_data.get("academic_info", {})
            course_id = academic_info.get("course_id") if academic_info else None
            school_id = student_data.get("school_id")
            
            course_name = ""
            school_name = ""
            
            # Obtener nombre del curso
            if course_id:
                course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
                course_name = course.course_name if course else ""
            
            # Obtener nombre del colegio (school_name desde schools)
            if school_id:
                school = db.query(SchoolModel).filter(SchoolModel.id == school_id).first()
                school_name = school.school_name if school else ""
            
            # Construir: curso - colegio
            if course_name and school_name:
                course_school_location = f"{course_name} - {school_name}".strip(" -")
            elif course_name:
                course_school_location = course_name
            elif school_name:
                course_school_location = school_name
            
            # Obtener datos del guardián
            parent_relation = ""
            parent_fullname = ""
            parent_rut = ""
            
            guardian_service = StudentGuardianClass(db)
            guardian_result = guardian_service.get(student_id)
            
            if guardian_result and isinstance(guardian_result, dict) and guardian_result.get("status") != "error":
                guardian_data = guardian_result
                
                # Obtener relación (family_member)
                family_member_id = guardian_data.get("family_member_id")
                if family_member_id:
                    family_member = db.query(FamilyMemberModel).filter(FamilyMemberModel.id == family_member_id).first()
                    parent_relation = family_member.family_member if family_member else ""
                
                # Obtener nombre completo del guardián
                guardian_names = guardian_data.get("names", "")
                guardian_father_lastname = guardian_data.get("father_lastname", "")
                guardian_mother_lastname = guardian_data.get("mother_lastname", "")
                parent_fullname = f"{guardian_names} {guardian_father_lastname} {guardian_mother_lastname}".strip()
                
                # Obtener RUT del guardián
                parent_rut = guardian_data.get("identification_number", "") or ""
            
            # Obtener ciudad/comuna del guardián (prioridad) o del estudiante (fallback)
            city = ""
            
            # Primero intentar obtener la ciudad del guardián
            if guardian_result and isinstance(guardian_result, dict) and guardian_result.get("status") != "error":
                city = guardian_result.get("city", "") or ""
            
            # Si no hay ciudad del guardián, obtenerla del estudiante
            if not city:
                personal_data = student_data.get("personal_data", {})
                commune_id = personal_data.get("commune_id")
                if commune_id:
                    commune = db.query(CommuneModel).filter(CommuneModel.id == commune_id).first()
                    if commune:
                        city = commune.commune or ""
            
            # Obtener día, mes y año actual
            from datetime import datetime
            now = datetime.now()
            day = str(now.day)
            
            # Meses en español con primera letra en mayúscula
            months_es = {
                1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
                5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
                9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
            }
            month_raw = months_es.get(now.month, str(now.month))
            # Capitalizar primera letra
            month = month_raw.capitalize() if month_raw else ""
            
            # Obtener año (últimos 2 dígitos) para completar 20[YEAR] → 2026
            year = str(now.year)[-2:]  # Ejemplo: 2026 → "26"
            
            # Generar el documento usando parent_authorization
            result = DocumentsClass.parent_authorization(
                original_file_path=str(template_path),
                student_fullname=student_fullname,
                parent_relation=parent_relation,
                student_course_school=course_school_location,
                parent_fullname=parent_fullname,
                parent_rut=parent_rut,
                city=city,
                day=day,
                month=month,
                year=year,  # Año (últimos 2 dígitos) para completar 20[YEAR]
                parent_signature="",  # Firma del padre/madre (se deja en blanco)
                yes_marker="●",  # Punto negro para [Y] (se hará más grande al insertar)
                no_marker="",  # En blanco para [N]
                output_directory="files/system/students"
            )
            
            if result["status"] == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", "Error generando documento de autorización"),
                        "data": None
                    }
                )
            
            # Guardar el documento generado en folders con document_id = 2
            try:
                generated_file = Path(result["file_path"])
                
                if generated_file.exists():
                    # Generar fecha y hora en formato YYYYMMDDHHMMSS
                    date_hour = datetime.now().strftime("%Y%m%d%H%M%S")
                    
                    # Obtener el document_type_id del documento (document_id = 2)
                    document_data = document_result if isinstance(document_result, dict) else {}
                    document_type_id = document_data.get("document_type_id")
                    
                    # Generar nombre del archivo: {student_id}_{document_id}_{document_type_id}_{date_hour}
                    file_extension = generated_file.suffix
                    unique_filename = f"{student_id}_{document_id}_{document_type_id}_{date_hour}{file_extension}"
                    
                    # Renombrar el archivo generado al nombre único
                    system_file_path = Path("files/system/students") / unique_filename
                    system_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Mover/renombrar el archivo
                    from shutil import move
                    move(generated_file, system_file_path)
                    
                    # Actualizar el resultado con la nueva ruta
                    result["file_path"] = str(system_file_path)
                    result["filename"] = unique_filename
                    
                    # Guardar directamente en folders con document_id = 2 (no usar store que busca por document_type_id)
                    # Asegurarse de usar document_id = 2 explícitamente (no la variable document_id que podría cambiar)
                    parent_auth_document_id = 2
                    
                    # Buscar la última versión para este estudiante y documento (document_id = 2)
                    last_version = db.query(FolderModel).filter(
                        FolderModel.student_id == student_id,
                        FolderModel.document_id == parent_auth_document_id  # Usar document_id = 2 directamente
                    ).order_by(FolderModel.version_id.desc()).first()
                    
                    # Determinar el nuevo version_id
                    if last_version:
                        new_version_id = last_version.version_id + 1
                    else:
                        new_version_id = 1
                    
                    # Crear el nuevo registro en folders con document_id = 2
                    new_folder = FolderModel(
                        student_id=student_id,
                        document_id=parent_auth_document_id,  # document_id = 2 para parent_authorization
                        version_id=new_version_id,
                        detail_id=None,  # No hay detail_id para parent_authorization
                        file=unique_filename,
                        added_date=datetime.now(),
                        updated_date=datetime.now()
                    )
                    
                    db.add(new_folder)
                    db.commit()
                    db.refresh(new_folder)
            except Exception as e:
                # Si falla el guardado en folders, continuar de todos modos
                pass
            
            # Retornar el archivo PDF generado
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type='application/pdf'
            )
        
        # Para otros document_id, buscar template y usar lógica genérica o específica según corresponda
        document_name = document_result.get("document", "") if isinstance(document_result, dict) else ""
        
        # Buscar template PDF - intentar diferentes formatos de nombre
        possible_template_names = [
            f"document_{document_id}.pdf",
            f"document_{document_id}_{document_type_id}.pdf",
            f"{document_name.replace(' ', '_')}.pdf",
            f"template_{document_id}.pdf",
            f"FU_{document_name.replace(' ', '_').upper()}.pdf"
        ]
        
        template_path = None
        for template_name in possible_template_names:
            test_path = Path("files/original_student_files") / template_name
            if test_path.exists():
                template_path = test_path
                break
        
        # Si no se encuentra template, retornar error informativo
        if not template_path:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": f"No se encontró template PDF para document_id {document_id}. Buscando templates con nombres: {', '.join(possible_template_names)}",
                    "data": {
                        "student_id": student_id,
                        "document_id": document_id,
                        "document_name": document_name,
                        "note": "Para document_id específicos, implementar método de generación correspondiente"
                    }
                }
            )
        
        # Por ahora, para otros tipos, retornar error indicando que necesita implementación específica
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content={
                "status": 501,
                "message": f"Generación de PDF para document_id {document_id} aún no implementada. Se requiere método específico para este tipo de documento.",
                "data": {
                    "student_id": student_id,
                    "document_id": document_id,
                    "document_name": document_name,
                    "template_found": str(template_path)
                }
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error generando documento: {str(e)}",
                "data": None
            }
        )

@documents.get("/download/{filename}")
async def download_document(
    filename: str
):
    try:
        file_path = Path("files/system/students") / filename
        
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
@documents.get("/inspect-pdf/{template_name}")
async def inspect_pdf_template(
    template_name: str
):
    """
    Inspecciona un template PDF para identificar qué campos de formulario contiene.
    Útil para entender cómo están estructurados los campos en el template PDF.
    """
    try:
        # Buscar el template PDF
        template_path = Path("files/original_student_files") / template_name
        
        if not template_path.exists():
            # Intentar con .pdf
            template_path = Path("files/original_student_files") / f"{template_name}.pdf"
        
        if not template_path.exists():
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": "Template PDF no encontrado",
                    "data": None
                }
            )
        
        result = DocumentsClass.inspect_pdf_form_fields(str(template_path))
        
        if result["status"] == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error inspeccionando template PDF"),
                    "data": None
                }
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Template PDF inspeccionado exitosamente",
                "data": {
                    "form_fields": result.get("form_fields", []),
                    "text_placeholders": result.get("text_placeholders", []),
                    "total_form_fields": result.get("total_form_fields", 0)
                }
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error inspeccionando template PDF: {str(e)}",
                "data": None
            }
        )
