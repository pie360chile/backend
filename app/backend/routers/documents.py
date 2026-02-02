from fastapi import APIRouter, status, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse, FileResponse
from app.backend.classes.documents_class import DocumentsClass
from app.backend.classes.student_class import StudentClass
from app.backend.classes.health_evaluation_class import HealthEvaluationClass
from app.backend.classes.progress_status_student_class import ProgressStatusStudentClass
from app.backend.classes.progress_status_individual_support_class import ProgressStatusIndividualSupportClass
from app.backend.classes.student_guardian_class import StudentGuardianClass
from app.backend.classes.individual_support_plan_class import IndividualSupportPlanClass
from app.backend.classes.fonoaudiological_report_class import FonoaudiologicalReportClass
from app.backend.classes.school_integration_program_exit_certificate_class import SchoolIntegrationProgramExitCertificateClass
from app.backend.db.database import get_db
from app.backend.db.models import (
    FolderModel,
    DocumentModel,
    GenderModel,
    NationalityModel,
    ProfessionalModel,
    FamilyMemberModel,
    CourseModel,
    SchoolModel,
    StudentAcademicInfoModel,
    StudentPersonalInfoModel,
    CommuneModel,
    SpecialEducationalNeedModel,
    StudentGuardianModel,
)
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
import json
from datetime import datetime, date
import uuid
from shutil import move

documents = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)


@documents.get("/debug/doc19/{student_id}")
async def debug_doc19_data(
    student_id: int,
    db: Session = Depends(get_db),
):
    """Devuelve los datos que se enviarían al PDF del documento 19 (para depurar)."""
    try:
        student_service = StudentClass(db)
        student_result = student_service.get(student_id)
        if isinstance(student_result, dict) and (student_result.get("error") or student_result.get("status") == "error"):
            return JSONResponse(status_code=404, content={"error": "Estudiante no encontrado"})
        ps_service = ProgressStatusIndividualSupportClass(db)
        ps_result = ps_service.get_by_student_id(student_id)
        if isinstance(ps_result, dict) and ps_result.get("status") == "error":
            return JSONResponse(status_code=404, content={"error": "No hay progress_status_individual_support para este estudiante"})
        ps_data = ps_result.copy()
        ps_data.pop("id", None)
        ps_data.pop("added_date", None)
        ps_data.pop("updated_date", None)
        student_data = student_result.get("student_data", {}) if isinstance(student_result, dict) else {}
        personal = student_data.get("personal_data") or {}
        academic = student_data.get("academic_info") or {}
        if not (ps_data.get("student_full_name") or "").strip():
            _fn = f"{personal.get('names') or ''} {personal.get('father_lastname') or ''} {personal.get('mother_lastname') or ''}".strip()
            ps_data["student_full_name"] = _fn if _fn else f"Estudiante {student_id}"
        if not (ps_data.get("student_identification_number") or "").strip():
            ps_data["student_identification_number"] = personal.get("identification_number") or student_data.get("identification_number") or ""
        if not (ps_data.get("student_born_date") or "").strip() and personal.get("born_date"):
            ps_data["student_born_date"] = personal.get("born_date")
        if not (ps_data.get("student_age") or "").strip() and personal.get("born_date"):
            try:
                born = datetime.strptime(str(personal.get("born_date")), "%Y-%m-%d").date()
                ref = datetime.now().date()
                if ps_data.get("progress_date"):
                    try:
                        ref = datetime.strptime(str(ps_data["progress_date"]), "%Y-%m-%d").date()
                    except Exception:
                        pass
                years = ref.year - born.year
                months = ref.month - born.month
                if months < 0:
                    years -= 1
                    months += 12
                ps_data["student_age"] = f"{years} año{'s' if years != 1 else ''}" if years > 0 else f"{months} mes{'es' if months != 1 else ''}"
            except Exception:
                pass
        if not ps_data.get("school_id") and not (ps_data.get("student_school") or "").strip():
            sid = student_data.get("school_id")
            if sid:
                ps_data["school_id"] = sid
        if not ps_data.get("student_course_id") and academic.get("course_id"):
            ps_data["student_course_id"] = academic.get("course_id")
        if not ps_data.get("student_nee_id") and academic.get("special_educational_need_id"):
            ps_data["student_nee_id"] = academic.get("special_educational_need_id")
        if not ps_data.get("guardian_relationship_id"):
            g_first = db.query(StudentGuardianModel).filter(StudentGuardianModel.student_id == student_id).order_by(StudentGuardianModel.id.desc()).first()
            if g_first:
                ps_data["guardian_relationship_id"] = g_first.id
        if ps_data.get("school_id"):
            school = db.query(SchoolModel).filter(SchoolModel.id == ps_data["school_id"]).first()
            if school and school.school_name:
                ps_data["student_school"] = school.school_name
            ps_data.pop("school_id", None)
        if not (ps_data.get("student_school") or "").strip() and student_data.get("school_id"):
            school = db.query(SchoolModel).filter(SchoolModel.id == student_data["school_id"]).first()
            if school and school.school_name:
                ps_data["student_school"] = school.school_name
        course_id = ps_data.get("student_course_id")
        if course_id:
            course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
            ps_data["course_name"] = course.course_name if course and course.course_name else ""
        else:
            ps_data["course_name"] = ""
        ps_data.pop("student_course_id", None)
        nee_id = ps_data.get("student_nee_id")
        if nee_id:
            nee = db.query(SpecialEducationalNeedModel).filter(SpecialEducationalNeedModel.id == nee_id).first()
            ps_data["nee_name"] = nee.special_educational_needs if nee and nee.special_educational_needs else ""
        else:
            ps_data["nee_name"] = ""
        ps_data.pop("student_nee_id", None)
        guardian_id = ps_data.get("guardian_relationship_id")
        if guardian_id:
            g = db.query(StudentGuardianModel).filter(StudentGuardianModel.id == guardian_id).first()
            if g:
                ps_data["guardian_fullname"] = f"{g.names or ''} {g.father_lastname or ''} {g.mother_lastname or ''}".strip()
                ps_data["guardian_rut"] = g.identification_number or ""
                if g.family_member_id:
                    fm = db.query(FamilyMemberModel).filter(FamilyMemberModel.id == g.family_member_id).first()
                    ps_data["guardian_relationship"] = fm.family_member if fm and fm.family_member else ""
                else:
                    ps_data["guardian_relationship"] = ""
            else:
                ps_data["guardian_fullname"] = ps_data.get("guardian_name") or ""
                ps_data["guardian_rut"] = ""
                ps_data["guardian_relationship"] = ""
        else:
            ps_data["guardian_fullname"] = ps_data.get("guardian_name") or ""
            ps_data["guardian_rut"] = ""
            ps_data["guardian_relationship"] = ""
        ps_data.pop("guardian_relationship_id", None)
        ps_data.pop("guardian_name", None)
        period_labels = {1: "1er Trimestre", 2: "2do Trimestre", 3: "1er Semestre", 4: "2do Semestre"}
        pid = ps_data.get("period_id")
        ps_data["period_label"] = period_labels.get(pid) if pid is not None else ""
        return JSONResponse(status_code=200, content={"data": ps_data})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


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

        # Obtener el documento por document_id para obtener su document_type_id (solo no eliminados)
        document = db.query(DocumentModel).filter(
            DocumentModel.id == document_id,
            DocumentModel.deleted_date.is_(None)
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
            professional_specialty_name = ""
            if evaluation_data.get("profesional_id"):
                professional = db.query(ProfessionalModel).filter(ProfessionalModel.id == evaluation_data.get("profesional_id")).first()
                if professional:
                    professional_fullname = f"{professional.names or ''} {professional.lastnames or ''}".strip()
                    # Obtener el nombre de la especialidad desde career_type_id
                    if professional.career_type_id:
                        from app.backend.db.models import CareerTypeModel
                        career_type = db.query(CareerTypeModel).filter(CareerTypeModel.id == professional.career_type_id).first()
                        if career_type and career_type.career_type:
                            professional_specialty_name = career_type.career_type
            
            # Si professional_specialty es un ID, intentar obtener el nombre
            if not professional_specialty_name and evaluation_data.get("professional_specialty"):
                try:
                    # Si es un número, es un ID
                    specialty_id = int(evaluation_data.get("professional_specialty"))
                    from app.backend.db.models import CareerTypeModel
                    career_type = db.query(CareerTypeModel).filter(CareerTypeModel.id == specialty_id).first()
                    if career_type and career_type.career_type:
                        professional_specialty_name = career_type.career_type
                except (ValueError, TypeError):
                    # Si no es un número, usar el valor directamente
                    professional_specialty_name = str(evaluation_data.get("professional_specialty", ""))
            
            # Agregar datos adicionales al evaluation_data
            evaluation_data["gender_name"] = gender_name
            evaluation_data["nationality_name"] = nationality_name
            evaluation_data["professional_fullname"] = professional_fullname
            evaluation_data["professional_specialty_name"] = professional_specialty_name
            
            # Fecha de nacimiento desde BD: si no viene en la evaluación, tomar del estudiante (student_personal_data)
            if not evaluation_data.get("born_date") and evaluation_data.get("student_id"):
                student_personal = db.query(StudentPersonalInfoModel).filter(
                    StudentPersonalInfoModel.student_id == evaluation_data["student_id"]
                ).first()
                if student_personal and student_personal.born_date:
                    # born_date en student_personal_data es String; normalizar a YYYY-MM-DD
                    bd_val = student_personal.born_date
                    if hasattr(bd_val, "strftime"):
                        evaluation_data["born_date"] = bd_val.strftime("%Y-%m-%d")
                    else:
                        evaluation_data["born_date"] = str(bd_val).strip()[:10]
                    # Recalcular edad si no venía en la evaluación
                    if evaluation_data.get("age") is None:
                        try:
                            bd_str = evaluation_data["born_date"][:10]
                            bd = datetime.strptime(bd_str, "%Y-%m-%d").date()
                            today = date.today()
                            evaluation_data["age"] = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
                        except Exception:
                            pass
            
            # Generar el documento PDF usando pypdf para rellenar campos AcroForm
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
            
            # Retornar el archivo PDF generado (solo descarga, no se guarda en folders)
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type='application/pdf'
            )
        
        # Si document_id = 18, generar documento de estado de avance (progress_status_students) desde cero
        if document_id == 18:
            # Buscar el estado de avance más reciente para este estudiante
            progress_status_service = ProgressStatusStudentClass(db)
            progress_statuses = progress_status_service.get_all(student_id=student_id)
            
            if not progress_statuses or len(progress_statuses) == 0:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": "No se encontró estado de avance para este estudiante",
                        "data": None
                    }
                )
            
            # Obtener el más reciente (primero de la lista)
            progress_status_data = progress_statuses[0]
            
            # Eliminar id y version_id (no van en el PDF)
            progress_status_data.pop("id", None)
            progress_status_data.pop("version_id", None)
            
            # Obtener datos adicionales del estudiante
            student_data = student_result.get("student_data", {}) if isinstance(student_result, dict) else {}
            personal_data = student_data.get("personal_data", {})
            student_name = personal_data.get("names", "") or ""
            student_lastname = f"{personal_data.get('father_lastname', '')} {personal_data.get('mother_lastname', '')}".strip()
            student_fullname = f"{student_name} {student_lastname}".strip()
            student_rut = personal_data.get("identification_number", "") or ""
            
            # Calcular edad del estudiante
            student_age = ""
            born_date_str = personal_data.get("born_date", "")
            if born_date_str:
                try:
                    # Intentar diferentes formatos de fecha
                    born_date = None
                    for date_format in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"]:
                        try:
                            born_date = datetime.strptime(born_date_str, date_format).date()
                            break
                        except:
                            continue
                    
                    if born_date:
                        # Calcular edad hasta la fecha del estado de avance o fecha actual
                        reference_date = datetime.now().date()
                        if progress_status_data.get("progress_date"):
                            try:
                                progress_date_str = progress_status_data.get("progress_date")
                                reference_date = datetime.strptime(progress_date_str, "%Y-%m-%d").date()
                            except:
                                pass
                        
                        # Calcular años y meses
                        years = reference_date.year - born_date.year
                        months = reference_date.month - born_date.month
                        if months < 0:
                            years -= 1
                            months += 12
                        elif months == 0 and reference_date.day < born_date.day:
                            years -= 1
                            months = 11
                        
                        if years > 0:
                            if months > 0:
                                student_age = f"{years} año{'s' if years != 1 else ''} y {months} mes{'es' if months != 1 else ''}"
                            else:
                                student_age = f"{years} año{'s' if years != 1 else ''}"
                        elif months > 0:
                            student_age = f"{months} mes{'es' if months != 1 else ''}"
                except Exception as e:
                    pass
            
            # Agregar datos del estudiante al progress_status_data
            progress_status_data["student_fullname"] = student_fullname
            progress_status_data["student_name"] = student_name
            progress_status_data["student_lastname"] = student_lastname
            progress_status_data["student_age"] = student_age
            progress_status_data["student_rut"] = student_rut
            
            # Convertir IDs a valores reales
            # school_id -> nombre de la escuela
            if progress_status_data.get("school_id"):
                school = db.query(SchoolModel).filter(SchoolModel.id == progress_status_data["school_id"]).first()
                progress_status_data["school_name"] = school.school_name if school and school.school_name else ""
                progress_status_data.pop("school_id", None)
            
            # nee_id -> nombre de la necesidad educativa especial
            if progress_status_data.get("nee_id"):
                nee = db.query(SpecialEducationalNeedModel).filter(SpecialEducationalNeedModel.id == progress_status_data["nee_id"]).first()
                progress_status_data["nee_name"] = nee.special_educational_needs if nee and nee.special_educational_needs else ""
                progress_status_data.pop("nee_id", None)
            
            # course_id -> nombre del curso
            if progress_status_data.get("course_id"):
                course = db.query(CourseModel).filter(CourseModel.id == progress_status_data["course_id"]).first()
                progress_status_data["course_name"] = course.course_name if course and course.course_name else ""
                progress_status_data.pop("course_id", None)
            
            # responsible_professionals -> convertir IDs a nombres (formato: "1,2,3")
            if progress_status_data.get("responsible_professionals"):
                professional_ids_str = str(progress_status_data["responsible_professionals"])
                if professional_ids_str:
                    try:
                        professional_ids = [int(id.strip()) for id in professional_ids_str.split(",") if id.strip().isdigit()]
                        professional_names = []
                        for prof_id in professional_ids:
                            professional = db.query(ProfessionalModel).filter(ProfessionalModel.id == prof_id).first()
                            if professional:
                                fullname = f"{professional.names or ''} {professional.lastnames or ''}".strip()
                                if fullname:
                                    professional_names.append(fullname)
                        progress_status_data["responsible_professionals_names"] = ", ".join(professional_names) if professional_names else ""
                    except Exception as e:
                        progress_status_data["responsible_professionals_names"] = ""
                progress_status_data.pop("responsible_professionals", None)
            
            # Generar el documento PDF desde cero (sin template)
            result = DocumentsClass.generate_document_pdf(
                document_id=document_id,
                document_data=progress_status_data,
                db=db,
                template_path=None,  # Siempre generar desde cero para documento 18
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
            
            # Retornar el archivo PDF generado
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type='application/pdf'
            )
        
        # Si document_id = 19, generar documento Estado de Avance PAI desde progress_status_individual_support
        if document_id == 19:
            ps_service = ProgressStatusIndividualSupportClass(db)
            ps_result = ps_service.get_by_student_id(student_id)
            if isinstance(ps_result, dict) and ps_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": "No se encontró estado de avance PAI para este estudiante",
                        "data": None,
                    },
                )
            ps_data = ps_result.copy()
            ps_data.pop("id", None)
            ps_data.pop("added_date", None)
            ps_data.pop("updated_date", None)

            # Completar datos faltantes desde student_data (estudiante, apoderado, escuela, curso, NEE)
            student_data = student_result.get("student_data", {}) if isinstance(student_result, dict) else {}
            personal = student_data.get("personal_data") or {}
            academic = student_data.get("academic_info") or {}
            if not (ps_data.get("student_full_name") or "").strip():
                _fn = f"{personal.get('names') or ''} {personal.get('father_lastname') or ''} {personal.get('mother_lastname') or ''}".strip()
                ps_data["student_full_name"] = _fn if _fn else f"Estudiante {student_id}"
            if not (ps_data.get("student_identification_number") or "").strip():
                ps_data["student_identification_number"] = personal.get("identification_number") or student_data.get("identification_number") or ""
            if not (ps_data.get("student_born_date") or "").strip() and personal.get("born_date"):
                ps_data["student_born_date"] = personal.get("born_date")
            if not (ps_data.get("student_age") or "").strip() and personal.get("born_date"):
                try:
                    born = datetime.strptime(str(personal.get("born_date")), "%Y-%m-%d").date()
                    ref = datetime.now().date()
                    if ps_data.get("progress_date"):
                        try:
                            ref = datetime.strptime(str(ps_data["progress_date"]), "%Y-%m-%d").date()
                        except Exception:
                            pass
                    years = ref.year - born.year
                    months = ref.month - born.month
                    if months < 0:
                        years -= 1
                        months += 12
                    ps_data["student_age"] = f"{years} año{'s' if years != 1 else ''}" if years > 0 else f"{months} mes{'es' if months != 1 else ''}"
                except Exception:
                    pass
            if not ps_data.get("school_id") and not (ps_data.get("student_school") or "").strip():
                sid = student_data.get("school_id")
                if sid:
                    ps_data["school_id"] = sid
            if not ps_data.get("student_course_id") and academic.get("course_id"):
                ps_data["student_course_id"] = academic.get("course_id")
            if not ps_data.get("student_nee_id") and academic.get("special_educational_need_id"):
                ps_data["student_nee_id"] = academic.get("special_educational_need_id")
            if not ps_data.get("guardian_relationship_id"):
                g_first = db.query(StudentGuardianModel).filter(
                    StudentGuardianModel.student_id == student_id
                ).order_by(StudentGuardianModel.id.desc()).first()
                if g_first:
                    ps_data["guardian_relationship_id"] = g_first.id

            # school_id -> nombre del establecimiento (si no hay student_school, resolver desde school_id)
            if ps_data.get("school_id"):
                school = db.query(SchoolModel).filter(SchoolModel.id == ps_data["school_id"]).first()
                if school and school.school_name:
                    ps_data["student_school"] = school.school_name
                ps_data.pop("school_id", None)
            if not (ps_data.get("student_school") or "").strip() and student_data.get("school_id"):
                school = db.query(SchoolModel).filter(SchoolModel.id == student_data["school_id"]).first()
                if school and school.school_name:
                    ps_data["student_school"] = school.school_name

            # student_course_id -> nombre del curso
            course_id = ps_data.get("student_course_id")
            if course_id:
                course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
                ps_data["course_name"] = course.course_name if course and course.course_name else ""
            else:
                ps_data["course_name"] = ""
            ps_data.pop("student_course_id", None)

            # student_nee_id -> nombre NEE
            nee_id = ps_data.get("student_nee_id")
            if nee_id:
                nee = db.query(SpecialEducationalNeedModel).filter(SpecialEducationalNeedModel.id == nee_id).first()
                ps_data["nee_name"] = nee.special_educational_needs if nee and nee.special_educational_needs else ""
            else:
                ps_data["nee_name"] = ""
            ps_data.pop("student_nee_id", None)

            # guardian_relationship_id -> apoderado completo desde student_guardians
            guardian_id = ps_data.get("guardian_relationship_id")
            if guardian_id:
                g = db.query(StudentGuardianModel).filter(StudentGuardianModel.id == guardian_id).first()
                if g:
                    ps_data["guardian_fullname"] = f"{g.names or ''} {g.father_lastname or ''} {g.mother_lastname or ''}".strip()
                    ps_data["guardian_rut"] = g.identification_number or ""
                    if g.family_member_id:
                        fm = db.query(FamilyMemberModel).filter(FamilyMemberModel.id == g.family_member_id).first()
                        ps_data["guardian_relationship"] = fm.family_member if fm and fm.family_member else ""
                    else:
                        ps_data["guardian_relationship"] = ""
                else:
                    ps_data["guardian_fullname"] = ps_data.get("guardian_name") or ""
                    ps_data["guardian_rut"] = ""
                    ps_data["guardian_relationship"] = ""
            else:
                ps_data["guardian_fullname"] = ps_data.get("guardian_name") or ""
                ps_data["guardian_rut"] = ""
                ps_data["guardian_relationship"] = ""
            ps_data.pop("guardian_relationship_id", None)
            ps_data.pop("guardian_name", None)

            # responsible_professionals (IDs separados por coma) -> nombres
            rp = ps_data.get("responsible_professionals")
            if rp:
                ids_str = str(rp).strip()
                ids = [int(x.strip()) for x in ids_str.split(",") if x.strip().isdigit()]
                names = []
                for pid in ids:
                    prof = db.query(ProfessionalModel).filter(ProfessionalModel.id == pid).first()
                    if prof:
                        fn = f"{prof.names or ''} {prof.lastnames or ''}".strip()
                        if fn:
                            names.append(fn)
                ps_data["responsible_professionals_names"] = ", ".join(names) if names else ""
            else:
                ps_data["responsible_professionals_names"] = ""
            ps_data.pop("responsible_professionals", None)

            # period_label: 1=1er Trimestre, 2=2do Trimestre, 3=1er Semestre, 4=2do Semestre
            period_labels = {1: "1er Trimestre", 2: "2do Trimestre", 3: "1er Semestre", 4: "2do Semestre"}
            pid = ps_data.get("period_id")
            ps_data["period_label"] = period_labels.get(pid) if pid is not None else ""

            result = DocumentsClass.generate_document_pdf(
                document_id=19,
                document_data=ps_data,
                db=db,
                template_path=None,
                output_directory="files/system/students",
            )
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", "Error generando estado de avance PAI"),
                        "data": None,
                    },
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf",
            )
        
        # Si document_id = 22, generar documento de Plan de Apoyo Individual
        if document_id == 22:
            # Buscar el Plan de Apoyo Individual más reciente para este estudiante
            isp_service = IndividualSupportPlanClass(db)
            isp_result = isp_service.get_by_student_id(student_id)
            
            if isinstance(isp_result, dict) and isp_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": "No se encontró Plan de Apoyo Individual para este estudiante",
                        "data": None
                    }
                )
            
            # Preparar datos para el PDF
            isp_data = isp_result.copy()
            
            # Eliminar campos que no van en el PDF
            isp_data.pop("id", None)
            isp_data.pop("added_date", None)
            isp_data.pop("updated_date", None)
            
            # Convertir IDs a valores reales
            # school_id -> nombre de la escuela
            if isp_data.get("school_id"):
                school = db.query(SchoolModel).filter(SchoolModel.id == isp_data["school_id"]).first()
                if school and school.school_name:
                    isp_data["student_school"] = school.school_name
                isp_data.pop("school_id", None)
            
            # student_nee_id -> nombre de la necesidad educativa especial
            if isp_data.get("student_nee_id"):
                nee = db.query(SpecialEducationalNeedModel).filter(SpecialEducationalNeedModel.id == isp_data["student_nee_id"]).first()
                if nee and nee.special_educational_needs:
                    isp_data["nee_name"] = nee.special_educational_needs
                isp_data.pop("student_nee_id", None)
            
            # student_course_id -> nombre del curso
            if isp_data.get("student_course_id"):
                course = db.query(CourseModel).filter(CourseModel.id == isp_data["student_course_id"]).first()
                if course and course.course_name:
                    isp_data["course_name"] = course.course_name
                isp_data.pop("student_course_id", None)
            
            # Procesar profesionales: obtener nombres y especialidades
            professionals = isp_data.get("professionals", [])
            if professionals:
                processed_professionals = []
                for prof in professionals:
                    professional_id = prof.get("professional_id")
                    career_type_id = prof.get("career_type_id")
                    
                    professional_name = ""
                    if professional_id:
                        professional = db.query(ProfessionalModel).filter(ProfessionalModel.id == professional_id).first()
                        if professional:
                            professional_name = f"{professional.names or ''} {professional.lastnames or ''}".strip()
                    
                    career_type_name = ""
                    if career_type_id:
                        from app.backend.db.models import CareerTypeModel
                        career_type = db.query(CareerTypeModel).filter(CareerTypeModel.id == career_type_id).first()
                        if career_type:
                            career_type_name = career_type.career_type
                    
                    processed_prof = prof.copy()
                    processed_prof["professional_name"] = professional_name
                    processed_prof["career_type_name"] = career_type_name
                    processed_professionals.append(processed_prof)
                
                isp_data["professionals"] = processed_professionals
            
            # Generar el documento PDF desde cero (sin template)
            result = DocumentsClass.generate_document_pdf(
                document_id=document_id,
                document_data=isp_data,
                db=db,
                template_path=None,  # Siempre generar desde cero para documento 22
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
            
            # Retornar el archivo PDF generado
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type='application/pdf'
            )
        
        # Si document_id = 8, generar Informe Fonoaudiológico desde cero
        if document_id == 8:
            fono_service = FonoaudiologicalReportClass(db)
            fono_result = fono_service.get_by_student_id(student_id)
            
            if isinstance(fono_result, dict) and fono_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": "No se encontró informe fonoaudiológico para este estudiante",
                        "data": None
                    }
                )
            
            report_data = fono_result.copy()
            report_data.pop("id", None)
            report_data.pop("added_date", None)
            report_data.pop("updated_date", None)
            
            # course_id -> nombre del curso
            if report_data.get("course_id"):
                course = db.query(CourseModel).filter(CourseModel.id == report_data["course_id"]).first()
                if course and course.course_name:
                    report_data["course_name"] = course.course_name
                report_data.pop("course_id", None)
            else:
                report_data["course_name"] = ""
            
            # establishment_id: si es numérico, opcionalmente resolver a nombre; si no, usar tal cual
            estab = report_data.get("establishment_id")
            if estab is not None and str(estab).strip().isdigit():
                try:
                    sid = int(estab)
                    school = db.query(SchoolModel).filter(SchoolModel.id == sid).first()
                    if school and school.school_name:
                        report_data["establishment_id"] = school.school_name
                except (ValueError, TypeError):
                    pass
            
            # responsible_professionals: list de IDs -> nombres
            rp = report_data.get("responsible_professionals")
            if rp is not None:
                ids = rp if isinstance(rp, list) else []
                if isinstance(rp, str):
                    try:
                        ids = json.loads(rp)
                    except Exception:
                        ids = []
                names = []
                for pid in ids:
                    try:
                        prof_id = int(pid)
                        professional = db.query(ProfessionalModel).filter(ProfessionalModel.id == prof_id).first()
                        if professional:
                            fn = f"{professional.names or ''} {professional.lastnames or ''}".strip()
                            if fn:
                                names.append(fn)
                    except (ValueError, TypeError):
                        pass
                report_data["responsible_professionals_names"] = ", ".join(names) if names else ""
            report_data.pop("responsible_professionals", None)
            
            result = DocumentsClass.generate_document_pdf(
                document_id=8,
                document_data=report_data,
                db=db,
                template_path=None,
                output_directory="files/system/students"
            )
            
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", "Error generando informe fonoaudiológico"),
                        "data": None
                    }
                )
            
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type='application/pdf'
            )
        
        # Si document_id = 23, generar Certificado de egreso PIE desde cero
        if document_id == 23:
            cert_service = SchoolIntegrationProgramExitCertificateClass(db)
            cert_result = cert_service.get_by_student_id(student_id)
            if isinstance(cert_result, dict) and cert_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": "No se encontró certificado de egreso PIE para este estudiante",
                        "data": None,
                    },
                )
            cert_data = cert_result.copy()
            cert_data.pop("id", None)
            cert_data.pop("added_date", None)
            cert_data.pop("updated_date", None)
            cert_data.pop("document_description", None)

            student_data = student_result.get("student_data", {}) if isinstance(student_result, dict) else {}
            personal = student_data.get("personal_data") or {}
            academic = student_data.get("academic_info") or {}
            _fn = f"{personal.get('names') or ''} {personal.get('father_lastname') or ''} {personal.get('mother_lastname') or ''}".strip()
            cert_data["student_full_name"] = _fn if _fn else f"Estudiante {student_id}"
            cert_data["student_rut"] = personal.get("identification_number") or student_data.get("identification_number") or ""

            school_id = student_data.get("school_id")
            if school_id:
                school = db.query(SchoolModel).filter(SchoolModel.id == school_id).first()
                cert_data["establishment_name"] = school.school_name if school and school.school_name else ""
            else:
                cert_data["establishment_name"] = ""
            course_id = academic.get("course_id")
            if course_id:
                course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
                cert_data["course_name"] = course.course_name if course and course.course_name else "Sin curso"
            else:
                cert_data["course_name"] = "Sin curso"
            nee_id = academic.get("special_educational_need_id")
            if nee_id:
                nee = db.query(SpecialEducationalNeedModel).filter(SpecialEducationalNeedModel.id == nee_id).first()
                cert_data["nee_name"] = nee.special_educational_needs if nee and nee.special_educational_needs else ""
            else:
                cert_data["nee_name"] = ""

            prof_id = cert_data.get("professional_id")
            if prof_id:
                prof = db.query(ProfessionalModel).filter(ProfessionalModel.id == prof_id).first()
                if prof:
                    cert_data["professional_fullname"] = f"{prof.names or ''} {prof.lastnames or ''}".strip()
                    cert_data["professional_rut"] = prof.identification_number or ""
                    _career = (cert_data.get("professional_career") or "").strip()
                    if _career:
                        cert_data["professional_role"] = _career
                    elif prof.career_type_id:
                        from app.backend.db.models import CareerTypeModel
                        ct = db.query(CareerTypeModel).filter(CareerTypeModel.id == prof.career_type_id).first()
                        cert_data["professional_role"] = ct.career_type if ct and ct.career_type else ""
                    else:
                        cert_data["professional_role"] = ""
                else:
                    cert_data["professional_fullname"] = cert_data["professional_rut"] = cert_data["professional_role"] = ""
            else:
                cert_data["professional_fullname"] = cert_data["professional_rut"] = cert_data["professional_role"] = ""
            cert_data.pop("professional_id", None)
            cert_data.pop("professional_certification_number", None)
            cert_data.pop("professional_career", None)

            guardian_id = cert_data.get("guardian_id")
            g = None
            if guardian_id:
                g = db.query(StudentGuardianModel).filter(StudentGuardianModel.id == guardian_id).first()
            if not g:
                g = db.query(StudentGuardianModel).filter(
                    StudentGuardianModel.student_id == student_id
                ).order_by(StudentGuardianModel.id.desc()).first()
            if g:
                cert_data["guardian_fullname"] = f"{g.names or ''} {g.father_lastname or ''} {g.mother_lastname or ''}".strip()
                cert_data["guardian_rut"] = g.identification_number or ""
            else:
                cert_data["guardian_fullname"] = cert_data["guardian_rut"] = ""
            cert_data.pop("guardian_id", None)

            result = DocumentsClass.generate_document_pdf(
                document_id=23,
                document_data=cert_data,
                db=db,
                template_path=None,
                output_directory="files/system/students",
            )
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", "Error generando certificado de egreso PIE"),
                        "data": None,
                    },
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf",
            )
        
        # Obtener datos del estudiante
        student_data = student_result.get("student_data", {}) if isinstance(student_result, dict) else {}
        student_name = student_data.get("full_name") or student_data.get("names") or f"Estudiante {student_id}"
        
        # Obtener document_type_id del documento
        document_type_id = document_result.get("document_type_id") if isinstance(document_result, dict) else None
        
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
        
        # Para otros document_id, usar la función general
        document_name = document_result.get("document", "") if isinstance(document_result, dict) else {}
        document_type_id = document_result.get("document_type_id") if isinstance(document_result, dict) else None
        
        # Obtener datos del estudiante
        student_data = student_result.get("student_data", {}) if isinstance(student_result, dict) else {}
        personal_data = student_data.get("personal_data", {})
        student_name = personal_data.get("names", "") or ""
        student_lastname = f"{personal_data.get('father_lastname', '')} {personal_data.get('mother_lastname', '')}".strip()
        student_fullname = f"{student_name} {student_lastname}".strip()
        
        # Preparar datos del documento
        document_data = {
            "student_id": student_id,
            "student_fullname": student_fullname,
            "student_name": student_name,
            "student_lastname": student_lastname,
            "document_id": document_id,
            "document_name": document_name,
            "document_title": document_name or f"Documento {document_id}"
        }
        
        # Buscar template PDF - intentar diferentes formatos de nombre
        possible_template_names = [
            f"document_{document_id}.pdf",
            f"document_{document_id}_{document_type_id}.pdf" if document_type_id else None,
            f"{document_name.replace(' ', '_')}.pdf" if document_name else None,
            f"template_{document_id}.pdf",
            f"FU_{document_name.replace(' ', '_').upper()}.pdf" if document_name else None
        ]
        
        # Filtrar None
        possible_template_names = [name for name in possible_template_names if name]
        
        template_path = None
        for template_name in possible_template_names:
            test_path = Path("files/original_student_files") / template_name
            if test_path.exists():
                template_path = test_path
                break
        
        # Generar el documento PDF usando la función general
        result = DocumentsClass.generate_document_pdf(
            document_id=document_id,
            document_data=document_data,
            db=db,
            template_path=str(template_path) if template_path else None,
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
        
        # Retornar el archivo PDF generado
        return FileResponse(
            path=result["file_path"],
            filename=result["filename"],
            media_type='application/pdf'
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
