from typing import Optional, Any
import unicodedata
from fastapi import APIRouter, status, UploadFile, File, Form, Depends, Body, Query
from fastapi.responses import JSONResponse, FileResponse
from app.backend.classes.documents_class import DocumentsClass
from app.backend.classes.docx_register_book_layout import (
    clone_register_book_section_b_blocks,
    clone_course_record_support_tables,
    clone_pai_support_tables,
    expand_raeg_intervention_rows,
    expand_learning_achievement_rows,
    apply_learning_achievement_period_top_spacing,
    clone_course_activity_record_blocks,
    clone_course_community_activity_blocks,
    clone_course_acta_reunion_blocks,
    expand_rafc_participant_rows,
    expand_tcee_participant_rows,
    expand_arn_participant_rows,
)
from app.backend.classes.course_activity_record_class import (
    _load_attendees,
    _row_to_dict,
    attendee_phone_cell,
    attendee_rut_cell,
    attendees_rafcnia_line,
    attendees_rafcnit_line,
)
from app.backend.classes.student_class import StudentClass
from app.backend.classes.health_evaluation_class import HealthEvaluationClass
from app.backend.classes.progress_status_student_class import ProgressStatusStudentClass
from app.backend.classes.progress_status_individual_support_class import ProgressStatusIndividualSupportClass
from app.backend.classes.student_guardian_class import StudentGuardianClass
from app.backend.classes.individual_support_plan_class import IndividualSupportPlanClass
from app.backend.classes.fonoaudiological_report_class import FonoaudiologicalReportClass
from app.backend.classes.school_integration_program_exit_certificate_class import SchoolIntegrationProgramExitCertificateClass
from app.backend.classes.anamnesis_class import AnamnesisClass
from app.backend.classes.family_report_class import FamilyReportClass
from app.backend.classes.interconsultation_class import InterconsultationClass
from app.backend.classes.guardian_attendance_certificate_class import GuardianAttendanceCertificateClass
from app.backend.classes.psychopedagogical_evaluation_class import PsychopedagogicalEvaluationClass
from app.backend.utils.psychoped_cognitive_quantitative import (
    AC_CONTENT_CONTROL_HOLD,
    CHART_PLACEHOLDER,
    inject_evalua_matrix_word_table,
    insert_chart_placeholder_paragraph_image,
    parse_evalua_psychoped_matrices,
    render_evalua_pt_line_chart_png,
    strip_chart_placeholder_from_docx,
)
from app.backend.classes.conners_teacher_evaluation_class import ConnersTeacherEvaluationClass
from app.backend.classes.cesp_class import CespClass
from app.backend.classes.action_incident_class import ActionIncidentClass
from app.backend.classes.idtel_report_class import IdtelReportClass
from app.backend.classes.psychomotor_evaluation_report_class import PsychomotorEvaluationReportClass
from app.backend.classes.pedagogical_evaluation_classroom_first_grade_class import PedagogicalEvaluationClassroomFirstGradeClass
from app.backend.classes.pedagogical_evaluation_classroom_second_grade_class import PedagogicalEvaluationClassroomSecondGradeClass
from app.backend.classes.pedagogical_evaluation_classroom_third_grade_class import PedagogicalEvaluationClassroomThirdGradeClass
from app.backend.classes.pedagogical_evaluation_classroom_fourth_grade_class import PedagogicalEvaluationClassroomFourthGradeClass
from app.backend.classes.pedagogical_evaluation_classroom_fifth_grade_class import PedagogicalEvaluationClassroomFifthGradeClass
from app.backend.classes.pedagogical_evaluation_classroom_sixth_grade_class import PedagogicalEvaluationClassroomSixthGradeClass
from app.backend.classes.pedagogical_evaluation_classroom_seventh_grade_class import PedagogicalEvaluationClassroomSeventhGradeClass
from app.backend.classes.pedagogical_evaluation_classroom_eighth_grade_class import PedagogicalEvaluationClassroomEighthGradeClass
from app.backend.classes.pedagogical_evaluation_classroom_first_grade_secondary_class import PedagogicalEvaluationClassroomFirstGradeSecondaryClass
from app.backend.classes.pedagogical_evaluation_classroom_second_grade_secondary_class import PedagogicalEvaluationClassroomSecondGradeSecondaryClass
from app.backend.classes.professional_document_assignment_class import ProfessionalDocumentAssignmentClass
from app.backend.db.database import get_db
from app.backend.db.models import (
    FolderModel,
    DocumentModel,
    GenderModel,
    NationalityModel,
    ProfessionalModel,
    UserModel,
    StudentModel,
    ProfessionalTeachingCourseModel,
    CoordinatorsCourseModel,
    MeetingSchedulalingModel,
    MeetingSchedualingAgreementModel,
    MeetingSchedualingRegisterProfessionalModel,
    DiversifiedStrategyModel,
    CollaborativeWorkModel,
    SupportOrganizationModel,
    DiversityCriterionModel,
    DiversityStrategyOptionModel,
    CourseDiversityResponseModel,
    CourseDiversityResponseStudentModel,
    CourseDiversityObservationModel,
    AdjustmentAspectModel,
    CourseAdjustmentModel,
    CourseAdjustmentStudentModel,
    CurricularAdequacyTypeModel,
    CourseCurricularAdequacyModel,
    CourseCurricularAdequacySubjectModel,
    CourseCurricularAdequacyStudentModel,
    EvalDiversityTypeModel,
    CourseEvalDiversityModel,
    CourseEvalDiversityObservationModel,
    CourseIndividualSupportModel,
    CourseIndividualSupportStudentModel,
    FamilyCommunityStrategyTypeModel,
    CourseFamilyCommunityModel,
    CourseFamilyCommunityObservationModel,
    CourseTeacherRecordActivityModel,
    CourseTeacherRecordObservationModel,
    CourseRecordSupportModel,
    CourseRecordSupportStudentModel,
    CourseRecordSupportInterventionModel,
    CourseLearningAchievementModel,
    CourseActivityFamilyModel,
    CourseActivityCommunityModel,
    CourseActivityOtherModel,
    DifferentiatedStrategiesImplementationModel,
    SubjectModel,
    FamilyMemberModel,
    CourseModel,
    SchoolModel,
    StudentAcademicInfoModel,
    StudentPersonalInfoModel,
    CommuneModel,
    RegionModel,
    SpecialEducationalNeedModel,
    StudentGuardianModel,
    InterconsultationModel,
    SupportAreaModel,
)
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import (
    UserLogin,
    CreateDocumentRequest,
    DocumentListRequest,
    UploadDocumentRequest
)
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path
import tempfile
import os
import re
import json
import logging
from datetime import datetime, date
from collections import defaultdict

logger = logging.getLogger(__name__)


def _catalog_row_is_informe_evaluacion_psicomotriz(document_id: int, db: Session) -> bool:
    """True si `document_id` es la fila del catálogo `documents` para Informe de evaluación psicomotriz."""
    row = (
        db.query(DocumentModel)
        .filter(DocumentModel.id == document_id, DocumentModel.deleted_date.is_(None))
        .first()
    )
    return bool(row and (row.document or "").strip() == "Informe de evaluación psicomotriz")


import uuid
from shutil import copy as shutil_copy, move

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
    period_year: Optional[int] = Query(
        None,
        ge=2000,
        le=2100,
        description="Año del período escolar (query; enviado por interceptor/cookie)",
    ),
    professional_id: Optional[int] = Query(
        None,
        ge=0,
        description="Profesional que sube el archivo (asignaciones Pie360)",
    ),
    course_id: Optional[int] = Query(
        None,
        ge=0,
        description="Curso del estudiante; si no viene, se usa academic_info del estudiante",
    ),
    db: Session = Depends(get_db),
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
        # Buscar la última versión para este estudiante, documento y período
        period_str = str(period_year) if period_year is not None else None
        lv_q = db.query(FolderModel).filter(
            FolderModel.student_id == student_id,
            FolderModel.document_id == document_id,
        )
        if period_str is not None:
            lv_q = lv_q.filter(FolderModel.period_year == period_str)
        last_version = lv_q.order_by(FolderModel.version_id.desc()).first()
        
        # Determinar el nuevo version_id
        if last_version:
            new_version_id = last_version.version_id + 1
        else:
            new_version_id = 1
        
        # Crear el nuevo registro en folders
        new_folder = FolderModel(
            school_id=None,
            course_id=None,
            student_id=student_id,
            document_id=document_id,
            version_id=new_version_id,
            detail_id=None,
            professional_id=0,
            file=unique_filename,
            period_year=period_str,
            added_date=datetime.now(),
            updated_date=datetime.now(),
            deleted_date=None,
        )
        
        db.add(new_folder)
        db.commit()
        db.refresh(new_folder)

        # Marcar asignaciones profesionales como completadas (status 1) si aplica
        try:
            ai = (student_data.get("academic_info") or {}) if isinstance(student_data, dict) else {}
            resolved_course = int(course_id) if course_id and int(course_id) > 0 else None
            if resolved_course is None and isinstance(ai, dict):
                c = ai.get("course_id")
                if c is not None and int(c) > 0:
                    resolved_course = int(c)
            ProfessionalDocumentAssignmentClass(db).mark_completed_after_folder_upload(
                period_year=period_year,
                student_id=student_id,
                document_catalog_id=int(document_id),
                document_type_id=int(document_type_id),
                professional_id=int(professional_id) if professional_id is not None else None,
                course_id=resolved_course,
            )
        except Exception:
            pass

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

def _generate_anamnesis_docx_internal(student_id: int, db: Session) -> dict:
    """
    Genera el documento DOCX de anamnesis para un estudiante.
    Retorna: {"status": "success", "file_path": str, "filename": str}
    o {"status": "error", "message": str, "status_code": int}
    """
    try:
        # --- 1. Obtener estudiante ---
        student_service = StudentClass(db)
        student_result = student_service.get(student_id)
        if isinstance(student_result, dict) and (student_result.get("error") or student_result.get("status") == "error"):
            return {"status": "error", "message": "Estudiante no encontrado", "status_code": 404}
        student_data = student_result.get("student_data", {}) or {}
        personal = student_data.get("personal_data", {}) or {}
        academic = student_data.get("academic_info", {}) or {}
        student_name = f"{personal.get('names', '') or ''} {personal.get('father_lastname', '') or ''} {personal.get('mother_lastname', '') or ''}".strip()
        if not student_name:
            student_name = f"Estudiante {student_id}"
        birth_day = ""
        age_years = ""
        age_months = ""
        born = personal.get("born_date")
        if born:
            try:
                if isinstance(born, str):
                    dt = datetime.strptime(str(born)[:10], "%Y-%m-%d").date() if len(str(born)) >= 10 else None
                else:
                    dt = born.date() if hasattr(born, "date") else born
                if dt:
                    birth_day = dt.strftime("%d/%m/%Y") if hasattr(dt, "strftime") else str(born)
                    today = date.today()
                    age_years = today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))
                    total_months = (today.year - dt.year) * 12 + (today.month - dt.month)
                    if today.day < dt.day:
                        total_months -= 1
                    age_months = total_months % 12
                    age_years = str(age_years)
                    age_months = str(age_months)
                else:
                    birth_day = str(born) if born else ""
            except Exception:
                birth_day = str(born) if born else ""
        female = "0"
        male = "0"
        gender_id = personal.get("gender_id")
        if gender_id and db:
            g = db.query(GenderModel).filter(GenderModel.id == gender_id).first()
            gn = str(g.gender).lower().strip() if g and g.gender else ""
            if gn:
                if "femenino" in gn or gn == "f" or "female" in gn or "mujer" in gn:
                    female, male = "1", "0"
                elif "masculino" in gn or gn == "m" or "male" in gn or "hombre" in gn:
                    female, male = "0", "1"
        birth_country = ""
        if personal.get("nationality_id") and db:
            nat = db.query(NationalityModel).filter(NationalityModel.id == personal.get("nationality_id")).first()
            if nat and nat.nationality:
                birth_country = str(nat.nationality).strip()
        address = str(personal.get("address") or "").strip()
        phone = str(personal.get("phone") or "").strip()
        mother_language = str(personal.get("native_language") or "").strip()
        used_language = str(personal.get("language_usually_used") or "").strip()
        course = ""
        school = ""
        if db:
            course_id = academic.get("course_id")
            if course_id:
                c = db.query(CourseModel).filter(CourseModel.id == course_id).first()
                course = str(c.course_name or "").strip() if c else ""
            school_id = student_data.get("school_id")
            if school_id:
                s = db.query(SchoolModel).filter(SchoolModel.id == school_id).first()
                school = str(s.school_name or "").strip() if s else ""
        ml_1 = ml_2 = ml_3 = ml_4 = ""
        ul_1 = ul_2 = ul_3 = ul_4 = ""
        anamnesis_service = AnamnesisClass(db)
        anamnesis_result = anamnesis_service.get_by_student_id(student_id)
        if isinstance(anamnesis_result, dict) and anamnesis_result.get("status") != "error":
            def _has_domain(arr, key):
                if not arr:
                    return False
                if isinstance(arr, str):
                    try:
                        arr = json.loads(arr) if arr else []
                    except Exception:
                        return False
                if isinstance(arr, list):
                    vals = [(str(x.get("value", x)) if isinstance(x, dict) else str(x)).lower().strip() for x in arr]
                    return key.lower() in vals
                if isinstance(arr, dict):
                    return bool(arr.get(key) or arr.get(key.capitalize()))
                return False
            nd = anamnesis_result.get("native_language_domain") or []
            ud = anamnesis_result.get("language_used_domain") or []
            if _has_domain(nd, "comprende") or _has_domain(nd, "understand"): ml_1 = "1"
            if _has_domain(nd, "habla") or _has_domain(nd, "speak"): ml_2 = "1"
            if _has_domain(nd, "lee") or _has_domain(nd, "read"): ml_3 = "1"
            if _has_domain(nd, "escribe") or _has_domain(nd, "write"): ml_4 = "1"
            if _has_domain(ud, "comprende") or _has_domain(ud, "understand"): ul_1 = "1"
            if _has_domain(ud, "habla") or _has_domain(ud, "speak"): ul_2 = "1"
            if _has_domain(ud, "lee") or _has_domain(ud, "read"): ul_3 = "1"
            if _has_domain(ud, "escribe") or _has_domain(ud, "write"): ul_4 = "1"
        informant_data = {"date": ["", "", "", ""], "name": ["", "", "", ""], "relation": ["", "", "", ""], "presence": ["", "", "", ""]}
        interviewer_data = {"date": ["", "", "", ""], "name": ["", "", "", ""], "rol": ["", "", "", ""]}
        fm_data = {"name": [""] * 8, "relation": [""] * 8, "age": [""] * 8, "schooling": [""] * 8, "occupation": [""] * 8}
        if isinstance(anamnesis_result, dict) and anamnesis_result.get("status") != "error":
            inf_list = anamnesis_result.get("informants") or []
            for i in range(min(4, len(inf_list))):
                inf = inf_list[i]
                informant_data["name"][i] = str(inf.get("name") or "").strip()
                informant_data["relation"][i] = str(inf.get("relationship") or "").strip()
                informant_data["presence"][i] = str(inf.get("presence") or "").strip()
                dt = inf.get("interview_date")
                if dt:
                    try:
                        if isinstance(dt, str) and len(dt) >= 10:
                            d = datetime.strptime(dt[:10], "%Y-%m-%d")
                            informant_data["date"][i] = d.strftime("%d/%m/%Y")
                        else:
                            informant_data["date"][i] = str(dt)
                    except Exception:
                        informant_data["date"][i] = str(dt)
            int_list = anamnesis_result.get("interviewers") or []
            for i in range(min(4, len(int_list))):
                inv = int_list[i]
                interviewer_data["rol"][i] = str(inv.get("role") or "").strip()
                dt = inv.get("interview_date")
                if dt:
                    try:
                        if isinstance(dt, str) and len(dt) >= 10:
                            d = datetime.strptime(dt[:10], "%Y-%m-%d")
                            interviewer_data["date"][i] = d.strftime("%d/%m/%Y")
                        else:
                            interviewer_data["date"][i] = str(dt)
                    except Exception:
                        interviewer_data["date"][i] = str(dt)
                pid = inv.get("professional_id")
                if pid and db:
                    prof = db.query(ProfessionalModel).filter(ProfessionalModel.id == pid).first()
                    if prof:
                        interviewer_data["name"][i] = f"{prof.names or ''} {prof.lastnames or ''}".strip()
            hm_list = anamnesis_result.get("household_members") or []
            for i in range(min(8, len(hm_list))):
                hm = hm_list[i]
                fm_data["name"][i] = str(hm.get("name") or "").strip()
                fm_data["relation"][i] = str(hm.get("relationship") or "").strip()
                fm_data["age"][i] = str(hm.get("age") or "").strip()
                fm_data["schooling"][i] = str(hm.get("schooling") or "").strip()
                fm_data["occupation"][i] = str(hm.get("occupation") or "").strip()
        spec_map = {
            "pediatry": "", "kinesiology": "", "genetic": "", "neurology": "",
            "speechtherapy": "", "another_diagnostic": "", "occupational_therapy": "",
            "educational_psychology": "", "psychiatry": "", "psychology": "",
        }
        _name_to_spec = {
            "pediatra": "pediatry", "kinesiología": "kinesiology", "kinesiologia": "kinesiology",
            "genética": "genetic", "genetica": "genetic", "neurología": "neurology", "neurologia": "neurology",
            "fonoaudiología": "speechtherapy", "fonoaudiologia": "speechtherapy",
            "otro": "another_diagnostic", "terapia ocupacional": "occupational_therapy",
            "psicopedagogía": "educational_psychology", "psicopedagogia": "educational_psychology",
            "psiquiatría": "psychiatry", "psiquiatria": "psychiatry",
            "psicología": "psychology", "psicologia": "psychology",
        }
        if isinstance(anamnesis_result, dict) and anamnesis_result.get("status") != "error":
            for item in anamnesis_result.get("specialists") or []:
                if isinstance(item, dict):
                    name = (item.get("name") or "").strip().lower()
                    status_val = str(item.get("status") or "").strip()
                    key = _name_to_spec.get(name)
                    if key:
                        spec_map[key] = status_val
        interview_reason = ""
        diagnosis_detail = ""
        dpy = dpn = bknormal = bkassisted = bkforceps = bkcesarean = bay = ban = fypcy = fypcn = fyvy = fyvn = "0"
        desnutritiony = desnutritionn = obesityy = obesityn = highfevery = highfevern = "0"
        seizuresy = seizuresn = hospitalizationsy = hospitalizationsn = injuy = injun = iny = inn = ay = an = "0"
        riy = rin = encpy = encpn = mgy = mgn = oy = on = "0"
        first_year_conditions_other_specify = birth_reason = first_year_notes = birth_weight = birth_height = ""
        dresses_alone = sits_alone = head_control = walks_without_support = first_words = first_phrases = ""
        control_sphincter_day = control_sphincter_night = bladder_sphincter_day = bladder_sphincter_night = ""
        sm_observations = ""
        ma_1 = ma_2 = ma_3 = ma_4 = mt_1 = mt_2 = mt_3 = mt_4 = "0"
        ldy = ldn = wsy = wsn = ffy = ffn = "0"
        fgraby = fgrabn = fgripy = fgripn = fpinchy = fpinchn = fdrawy = fdrawn = fwritey = fwriten = fthready = fthreadn = "0"
        vqy = ["0"] * 16
        vqn = ["0"] * 16
        cqy = ["0"] * 8
        cqn = ["0"] * 8
        dlq_1 = dlq_2 = dlq_3 = dlq_4 = "0"
        dlq = ""
        cley = ["0"] * 6
        clen = ["0"] * 6
        clcy = ["0"] * 8
        clcn = ["0"] * 8
        clc_text = ""
        dsy = ["0"] * 12
        dsn = ["0"] * 12
        cshy = ["0"] * 11
        cshn = ["0"] * 11
        csh_text = ""
        family_medical_history = ""
        family_medical_observation = ""
        sq = ["0"] * 6
        feed_1 = feed_2 = feed_3 = feed_4 = "0"
        feed_other_text = ""
        weight_1 = weight_2 = weight_3 = "0"
        sleep_1 = sleep_2 = sleep_3 = "0"
        sleep_time = ""
        badsleep_1 = badsleep_2 = badsleep_3 = badsleep_4 = badsleep_5 = "0"
        howsleep1 = howsleep2 = "0"
        howsleep = ""
        mood1 = mood2 = mood3 = mood4 = mood5 = mood6 = mood7 = mood8 = "0"
        another_mood = ""
        enter_schooling_age = ""
        kindergarten1 = kindergarten2 = "0"
        school_assisted_number = ""
        teaching1 = teaching2 = teaching3 = "0"
        why_change_of_school = ""
        repeatedcourse1 = repeatedcourse2 = "0"
        courses = ""
        why_repeated = ""
        current_level = ""
        current_situation = ["0"] * 14  # 7 items × (Sí, No) para Situación actual
        family_attitude = ["0"] * 28  # Actitud de la familia
        family_attitude_performance_reasons = ""
        family_attitude_response_difficulties_other = ""
        family_attitude_response_success_other = ""
        family_attitude_rewards_other = ""
        final_comments = ""
        if isinstance(anamnesis_result, dict) and anamnesis_result.get("status") != "error":
            interview_reason = str(anamnesis_result.get("interview_reason") or "").strip()
            diagnosis_detail = str(anamnesis_result.get("diagnosis_detail") or "").strip()
            dh = anamnesis_result.get("diagnosis_has")
            if dh == 1: dpy = "1"
            elif dh == 2: dpn = "1"
            bt = anamnesis_result.get("birth_type_id")
            if bt == 1: bknormal = "1"
            elif bt == 2: bkassisted = "1"
            elif bt == 3: bkforceps = "1"
            elif bt == 4: bkcesarean = "1"
            bma = anamnesis_result.get("birth_medical_assistance")
            if bma == 1: bay = "1"
            elif bma == 2: ban = "1"
            fypc = anamnesis_result.get("first_year_periodic_health_checkups")
            if fypc == 1: fypcy = "1"
            elif fypc == 2: fypcn = "1"
            fyv = anamnesis_result.get("first_year_vaccines")
            if fyv == 1: fyvy = "1"
            elif fyv == 2: fyvn = "1"
            fyc = anamnesis_result.get("first_year_conditions") or {}
            if isinstance(fyc, str):
                try:
                    fyc = json.loads(fyc) if fyc else {}
                except Exception:
                    fyc = {}
            _des = fyc.get("desnutricion") if isinstance(fyc, dict) else None
            if _des == 1: desnutritiony = "1"
            elif _des == 2: desnutritionn = "1"
            _obs = fyc.get("obesidad") if isinstance(fyc, dict) else None
            if _obs == 1: obesityy = "1"
            elif _obs == 2: obesityn = "1"
            _hf = fyc.get("fiebre_alta") if isinstance(fyc, dict) else None
            if _hf == 1: highfevery = "1"
            elif _hf == 2: highfevern = "1"
            _sz = fyc.get("convulsiones") if isinstance(fyc, dict) else None
            if _sz == 1: seizuresy = "1"
            elif _sz == 2: seizuresn = "1"
            _hosp = fyc.get("hospitalizaciones") if isinstance(fyc, dict) else None
            if _hosp == 1: hospitalizationsy = "1"
            elif _hosp == 2: hospitalizationsn = "1"
            _inj = fyc.get("traumatismos") if isinstance(fyc, dict) else None
            if _inj == 1: injuy = "1"
            elif _inj == 2: injun = "1"
            _intox = fyc.get("intoxicacion") if isinstance(fyc, dict) else None
            if _intox == 1: iny = "1"
            elif _intox == 2: inn = "1"
            _asma = fyc.get("asma") if isinstance(fyc, dict) else None
            if _asma == 1: ay = "1"
            elif _asma == 2: an = "1"
            _resp = fyc.get("enfermedad_respiratoria") if isinstance(fyc, dict) else None
            if _resp == 1: riy = "1"
            elif _resp == 2: rin = "1"
            _enc = fyc.get("encefalitis") if isinstance(fyc, dict) else None
            if _enc == 1: encpy = "1"
            elif _enc == 2: encpn = "1"
            _men = fyc.get("meningitis") if isinstance(fyc, dict) else None
            if _men == 1: mgy = "1"
            elif _men == 2: mgn = "1"
            _otro = fyc.get("otro") if isinstance(fyc, dict) else None
            if _otro == 1: oy = "1"
            elif _otro == 2: on = "1"
            _otras = fyc.get("otras") if isinstance(fyc, dict) else None
            first_year_conditions_other_specify = str(_otras or anamnesis_result.get("first_year_conditions_other_specify") or "").strip()
            birth_reason = str(anamnesis_result.get("birth_reason") or "").strip()
            first_year_notes = str(anamnesis_result.get("first_year_notes") or "").strip()
            birth_weight = str(anamnesis_result.get("birth_weight") or "").strip()
            birth_height = str(anamnesis_result.get("birth_height") or "").strip()
            dresses_alone = str(anamnesis_result.get("sm_dresses_alone") or "").strip()
            sits_alone = str(anamnesis_result.get("sm_sits_alone") or "").strip()
            head_control = str(anamnesis_result.get("sm_head_control") or "").strip()
            walks_without_support = str(anamnesis_result.get("sm_walks_without_support") or "").strip()
            first_words = str(anamnesis_result.get("sm_first_words") or "").strip()
            first_phrases = str(anamnesis_result.get("sm_first_phrases") or "").strip()
            control_sphincter_day = str(anamnesis_result.get("sm_bowel_day") or "").strip()
            control_sphincter_night = str(anamnesis_result.get("sm_bowel_night") or "").strip()
            bladder_sphincter_day = str(anamnesis_result.get("sm_bladder_day") or "").strip()
            bladder_sphincter_night = str(anamnesis_result.get("sm_bladder_night") or "").strip()
            sm_observations = str(anamnesis_result.get("sm_observations_1") or "").strip()
            _ma = (str(anamnesis_result.get("sm_motor_activity") or "").strip().lower() if anamnesis_result.get("sm_motor_activity") is not None else "")
            if _ma in ("normal",): ma_1 = "1"
            elif _ma in ("activo",): ma_2 = "1"
            elif _ma in ("hiperactivo",): ma_3 = "1"
            elif _ma in ("hipoactivo",): ma_4 = "1"
            _mt = (str(anamnesis_result.get("sm_muscle_tone") or "").strip().lower() if anamnesis_result.get("sm_muscle_tone") is not None else "")
            if _mt in ("normal",): mt_1 = "1"
            elif _mt in ("hipertónico", "hiertonico", "hipertonico"): mt_2 = "1"
            elif _mt in ("hipotónico", "hipotonico", "hipotónico"): mt_3 = "1"
            _ws = anamnesis_result.get("sm_walking_stability")
            if _ws == 1: wsy = "1"
            elif _ws == 2: wsn = "1"
            _ff = anamnesis_result.get("sm_frequent_falls")
            if _ff == 1: ffy = "1"
            elif _ff == 2: ffn = "1"
            _ld = anamnesis_result.get("sm_lateral_dominance")
            if _ld is not None:
                _ld_s = str(_ld).strip().lower()
                if _ld_s in ("der", "der.", "derecha", "d", "right", "1") or _ld == 1: ldy = "1"
                elif _ld_s in ("izq", "izq.", "izquierda", "i", "left", "2") or _ld == 2: ldn = "1"
            def _fine_yn(val):
                if val == 1: return ("1", "0")
                if val == 2: return ("0", "1")
                return ("0", "0")
            for fn, setter in [("sm_fine_grab", lambda v: (None, None) if v is None else (f"fgraby={_fine_yn(v)[0]}", f"fgrabn={_fine_yn(v)[1]}")), ("sm_fine_grip", lambda v: (None, None) if v is None else (f"fgripy={_fine_yn(v)[0]}", f"fgripn={_fine_yn(v)[1]}")), ("sm_fine_pinch", lambda v: (None, None) if v is None else (f"fpinchy={_fine_yn(v)[0]}", f"fpinchn={_fine_yn(v)[1]}")), ("sm_fine_draw", lambda v: (None, None) if v is None else (f"fdrawy={_fine_yn(v)[0]}", f"fdrawn={_fine_yn(v)[1]}")), ("sm_fine_write", lambda v: (None, None) if v is None else (f"fwritey={_fine_yn(v)[0]}", f"fwriten={_fine_yn(v)[1]}")), ("sm_fine_thread", lambda v: (None, None) if v is None else (f"fthready={_fine_yn(v)[0]}", f"fthreadn={_fine_yn(v)[1]}"))]:
                v = anamnesis_result.get(fn)
                if v is not None:
                    yv, nv = _fine_yn(v)
                    if fn == "sm_fine_grab": fgraby, fgrabn = yv, nv
                    elif fn == "sm_fine_grip": fgripy, fgripn = yv, nv
                    elif fn == "sm_fine_pinch": fpinchy, fpinchn = yv, nv
                    elif fn == "sm_fine_draw": fdrawy, fdrawn = yv, nv
                    elif fn == "sm_fine_write": fwritey, fwriten = yv, nv
                    elif fn == "sm_fine_thread": fthready, fthreadn = yv, nv
        _vq_fields = ("vision_interested_stimuli", "vision_irritated_eyes", "vision_headaches", "vision_squints", "vision_follows_movement", "vision_abnormal_movements", "vision_erroneous_behaviors", "vision_diagnosis", "hearing_interested_stimuli", "hearing_recognizes_voices", "hearing_turns_head", "hearing_ears_to_tv", "hearing_covers_ears", "hearing_earaches", "hearing_pronunciation_adequate", "hearing_diagnosis")
        for i, fn in enumerate(_vq_fields):
            if i >= 16: break
            v = anamnesis_result.get(fn)
            if v == 1: vqy[i] = "1"
            elif v == 2: vqn[i] = "1"
        _cq_fields = ("sm_cog_reacts_familiar", "sm_cog_manipulates_explores", "sm_cog_demands_company", "sm_cog_understands_prohibitions", "sm_cog_smiles_babbles", "sm_cog_poor_eye_hand", None, None)
        for i, fn in enumerate(_cq_fields):
            if i >= 8 or fn is None: break
            v = anamnesis_result.get(fn)
            try: v = int(v) if v is not None else None
            except (TypeError, ValueError): v = None
            if v == 1: cqy[i] = "1"
            elif v == 2: cqn[i] = "1"
        _lcm = (str(anamnesis_result.get("language_communication_method") or "").strip().lower() if anamnesis_result.get("language_communication_method") is not None else "")
        dlq_1 = "1" if _lcm == "oral" else "0"
        dlq_2 = "1" if _lcm == "gestual" else "0"
        dlq_3 = "1" if _lcm == "mixto" else "0"
        dlq_4 = "1" if _lcm == "otro" else "0"
        dlq = str(anamnesis_result.get("language_communication_other") or "").strip()
        _cle_fields = ("language_exp_babbles", "language_exp_emits_phrases", "language_exp_vocalizes_gestures", "language_exp_relates_experiences", "language_exp_emits_words", "language_exp_clear_pronunciation")
        cley = ["0"] * 6
        clen = ["0"] * 6
        for i, fn in enumerate(_cle_fields):
            if i >= 6: break
            v = anamnesis_result.get(fn)
            try: v = int(v) if v is not None else None
            except (TypeError, ValueError): v = None
            if v == 1: cley[i] = "1"
            elif v == 2: clen[i] = "1"
        _clc_fields = ("language_comp_identifies_objects", "language_comp_follows_simple_instructions", "language_comp_identifies_people", "language_comp_follows_complex_instructions", "language_comp_understands_abstract", "language_comp_follows_group_instructions", "language_comp_responds_coherently", "language_comp_understands_stories")
        clcy = ["0"] * 8
        clcn = ["0"] * 8
        for i, fn in enumerate(_clc_fields):
            if i >= 8: break
            v = anamnesis_result.get(fn)
            try: v = int(v) if v is not None else None
            except (TypeError, ValueError): v = None
            if v == 1: clcy[i] = "1"
            elif v == 2: clcn[i] = "1"
        clc_text = str(anamnesis_result.get("language_oral_loss") or "").strip()
        _ds_fields = ("social_relates_spontaneously", "social_relates_collaboratively", "social_explains_behaviors", "social_respects_social_norms", "social_participates_groups", "social_respects_school_norms", "social_prefers_individual", "social_shows_humor", "social_echolalic_language", "social_stereotyped_movements", "social_difficulty_adapting", "social_frequent_tantrums")
        for i, fn in enumerate(_ds_fields):
            if i >= 12: break
            v = anamnesis_result.get(fn)
            try: v = int(v) if v is not None else None
            except (TypeError, ValueError): v = None
            if v == 1: dsy[i] = "1"
            elif v == 2: dsn[i] = "1"
        _csh_fields = ("health_vaccines_up_to_date", "health_epilepsy", "health_heart_problems", "health_paraplegia", "health_hearing_loss", "health_vision_loss", "health_motor_disorder", "health_bronchorespiratory", "health_infectious_disease", "health_emotional_disorder", "health_behavioral_disorder")
        for i, fn in enumerate(_csh_fields):
            if i >= 11: break
            v = anamnesis_result.get(fn)
            try: v = int(v) if v is not None else None
            except (TypeError, ValueError): v = None
            if v == 1: cshy[i] = "1"
            elif v == 2: cshn[i] = "1"
        csh_text = str(anamnesis_result.get("health_other_specify") or "").strip()
        family_medical_history = str(anamnesis_result.get("family_health_history") or "").strip()
        family_medical_observation = str(anamnesis_result.get("family_health_observations") or "").strip()
        _sl = (str(anamnesis_result.get("social_reaction_lights") or "").strip().lower() if anamnesis_result.get("social_reaction_lights") is not None else "")
        if _sl == "natural": sq[0] = "1"
        elif _sl == "desmesurada": sq[1] = "1"
        _ss = (str(anamnesis_result.get("social_reaction_sounds") or "").strip().lower() if anamnesis_result.get("social_reaction_sounds") is not None else "")
        if _ss == "natural": sq[2] = "1"
        elif _ss == "desmesurada": sq[3] = "1"
        _sp = (str(anamnesis_result.get("social_reaction_strange_people") or "").strip().lower() if anamnesis_result.get("social_reaction_strange_people") is not None else "")
        if _sp == "natural": sq[4] = "1"
        elif _sp == "desmesurada": sq[5] = "1"
        _fd = (str(anamnesis_result.get("health_diet") or "").strip().lower() if anamnesis_result.get("health_diet") is not None else "")
        if _fd == "normal": feed_1 = "1"
        elif _fd in ("malo", "mala", "malo/a", "malo para comer", "mala para comer"): feed_2 = "1"
        elif _fd in ("bueno", "buena", "bueno/a", "bueno para comer", "buena para comer"): feed_3 = "1"
        elif _fd == "otro": feed_4 = "1"
        feed_other_text = str(anamnesis_result.get("health_diet_other") or "").strip()
        _hw = (str(anamnesis_result.get("health_weight") or "").strip().lower() if anamnesis_result.get("health_weight") is not None else "")
        if _hw == "normal": weight_1 = "1"
        elif _hw in ("bajo", "bajo peso"): weight_2 = "1"
        elif _hw in ("obesidad", "obeso"): weight_3 = "1"
        _spat = (str(anamnesis_result.get("health_sleep_pattern") or "").strip().lower() if anamnesis_result.get("health_sleep_pattern") is not None else "")
        if _spat == "normal": sleep_1 = "1"
        elif _spat == "tranquilo": sleep_2 = "1"
        elif _spat == "inquieto": sleep_3 = "1"
        sleep_time = str(anamnesis_result.get("health_sleep_hours") or "").strip()
        _bds = (anamnesis_result.get("health_sleep_insomnia"), anamnesis_result.get("health_sleep_nightmares"), anamnesis_result.get("health_sleep_terrors"), anamnesis_result.get("health_sleep_sleepwalking"), anamnesis_result.get("health_sleep_good_mood"))
        badsleep_1 = "1" if (_bds[0] and int(_bds[0])) else "0"
        badsleep_2 = "1" if (_bds[1] and int(_bds[1])) else "0"
        badsleep_3 = "1" if (_bds[2] and int(_bds[2])) else "0"
        badsleep_4 = "1" if (_bds[3] and int(_bds[3])) else "0"
        badsleep_5 = "1" if (_bds[4] and int(_bds[4])) else "0"
        _hsa = (str(anamnesis_result.get("health_sleeps_alone") or "").strip().lower() if anamnesis_result.get("health_sleeps_alone") is not None else "")
        if _hsa == "solo": howsleep1 = "1"
        elif _hsa in ("acompañado", "acompanado"): howsleep2 = "1"
        howsleep = str(anamnesis_result.get("health_sleeps_specify") or "").strip()
        _hmb = (str(anamnesis_result.get("health_mood_behavior") or "").strip().lower() if anamnesis_result.get("health_mood_behavior") is not None else "")
        if _hmb:
            for p in [x.strip() for x in _hmb.replace(",", " ").split() if x.strip()] or [_hmb]:
                if p == "alegre": mood1 = "1"
                elif p in ("juguetón", "jugueton", "bromista", "juguetón/bromista"): mood2 = "1"
                elif p in ("risueño", "risueña", "risueno", "risueño(a)", "risueño/a"): mood3 = "1"
                elif p == "triste": mood4 = "1"
                elif p == "serio": mood5 = "1"
                elif p == "rebelde": mood6 = "1"
                elif p in ("apático", "apatico", "apática", "apatica"): mood7 = "1"
                elif p in ("violento", "violenta", "violento(a)", "violento/a"): mood8 = "1"
        another_mood = str(anamnesis_result.get("health_mood_other") or "").strip()
        enter_schooling_age = str(anamnesis_result.get("school_entry_age") or "").strip()
        _ak = anamnesis_result.get("attended_kindergarten")
        if _ak == 1: kindergarten1 = "1"
        elif _ak == 2: kindergarten2 = "1"
        school_assisted_number = str(anamnesis_result.get("schools_count") or "").strip()
        _tm = (str(anamnesis_result.get("teaching_modality") or "").strip().lower() if anamnesis_result.get("teaching_modality") is not None else "")
        if _tm == "regular": teaching1 = "1"
        elif _tm == "especial": teaching2 = "1"
        elif _tm in ("técnica", "tecnica", "técnico", "tecnico"): teaching3 = "1"
        why_change_of_school = str(anamnesis_result.get("changes_reason") or "").strip()
        _cs_fields = (
            ("learning_difficulty", 0, 1),
            ("participation_difficulty", 2, 3),
            ("disruptive_behavior", 4, 5),
            ("attends_regularly", 6, 7),
            ("attends_gladly", 8, 9),
            ("family_support_homework", 10, 11),
            ("friends", 12, 13),
        )
        for fn, idx_y, idx_n in _cs_fields:
            v = anamnesis_result.get(fn)
            try:
                v = int(v) if v is not None else None
            except (TypeError, ValueError):
                v = None
            if v == 1:
                current_situation[idx_y] = "1"
            elif v == 2:
                current_situation[idx_n] = "1"
        _rc = anamnesis_result.get("repeated_grade")
        if _rc == 1:
            repeatedcourse1 = "1"
        elif _rc == 2:
            repeatedcourse2 = "1"
        elif (str(anamnesis_result.get("repeated_courses") or "").strip() or str(anamnesis_result.get("repeated_reason") or "").strip()):
            repeatedcourse1 = "1"
        else:
            repeatedcourse2 = "1"
        courses = str(anamnesis_result.get("repeated_courses") or "").strip()
        why_repeated = str(anamnesis_result.get("repeated_reason") or "").strip()
        current_level = str(anamnesis_result.get("current_level") or "").strip()
        if not current_level:
            current_level = course  # Fallback: usar curso del estudiante si current_level está vacío
        # Actitud de la familia (family_attitude1-28)
        def _in_arr(arr, key):
            """Comprueba si key está en arr (array de strings o de dicts con value)."""
            if not arr:
                return False
            if isinstance(arr, str):
                try:
                    arr = json.loads(arr) if arr else []
                except Exception:
                    return False
            if isinstance(arr, list):
                vals = [(str(x.get("value", x)) if isinstance(x, dict) else str(x)) for x in arr]
                return any(key.lower() in str(v).lower() for v in vals)
            return False
        _pa = (str(anamnesis_result.get("performance_assessment") or "").strip().lower()
               if anamnesis_result.get("performance_assessment") is not None else "")
        if "satisfactorio" in _pa:
            family_attitude[0] = "1"
        elif "insatisfactorio" in _pa:
            family_attitude[1] = "1"
        family_attitude_performance_reasons = str(anamnesis_result.get("performance_reasons") or "").strip()
        _rd = anamnesis_result.get("response_difficulties") or []
        if isinstance(_rd, str):
            try:
                _rd = json.loads(_rd) if _rd else []
            except Exception:
                _rd = []
        if _in_arr(_rd, "apoyo"):
            family_attitude[2] = "1"
        if _in_arr(_rd, "castigo"):
            family_attitude[3] = "1"
        if _in_arr(_rd, "indiferencia"):
            family_attitude[4] = "1"
        if _in_arr(_rd, "compasión") or _in_arr(_rd, "compasion"):
            family_attitude[5] = "1"
        if _in_arr(_rd, "tensión") or _in_arr(_rd, "tension"):
            family_attitude[6] = "1"
        if _in_arr(_rd, "otra"):
            family_attitude[7] = "1"
        family_attitude_response_difficulties_other = str(anamnesis_result.get("response_difficulties_other") or "").strip()
        _rs = anamnesis_result.get("response_success") or []
        if isinstance(_rs, str):
            try:
                _rs = json.loads(_rs) if _rs else []
            except Exception:
                _rs = []
        if _in_arr(_rs, "apoyo"):
            family_attitude[8] = "1"
        if _in_arr(_rs, "indiferencia"):
            family_attitude[9] = "1"
        if _in_arr(_rs, "otra"):
            family_attitude[10] = "1"
        family_attitude_response_success_other = str(anamnesis_result.get("response_success_other") or "").strip()
        _rw = anamnesis_result.get("rewards") or []
        if isinstance(_rw, str):
            try:
                _rw = json.loads(_rw) if _rw else []
            except Exception:
                _rw = []
        if _in_arr(_rw, "expresiones afectivas"):
            family_attitude[11] = "1"
        if _in_arr(_rw, "alimentos preferidos"):
            family_attitude[12] = "1"
        if _in_arr(_rw, "ver tv") or _in_arr(_rw, "ver televisión"):
            family_attitude[13] = "1"
        if _in_arr(_rw, "juguetes"):
            family_attitude[14] = "1"
        if _in_arr(_rw, "tiempo libre"):
            family_attitude[15] = "1"
        if _in_arr(_rw, "otro") or _in_arr(_rw, "otros"):
            family_attitude[16] = "1"
        family_attitude_rewards_other = str(anamnesis_result.get("rewards_other") or "").strip()
        _sp = anamnesis_result.get("supporters") or []
        if isinstance(_sp, str):
            try:
                _sp = json.loads(_sp) if _sp else []
            except Exception:
                _sp = []
        if _in_arr(_sp, "madre"):
            family_attitude[17] = "1"
        if _in_arr(_sp, "padre"):
            family_attitude[18] = "1"
        if _in_arr(_sp, "hermanos") or _in_arr(_sp, "hermanas"):
            family_attitude[19] = "1"
        if _in_arr(_sp, "otros familiares"):
            family_attitude[20] = "1"
        if _in_arr(_sp, "otros profesionales"):
            family_attitude[21] = "1"
        _ex = (str(anamnesis_result.get("expectations") or "").strip().lower()
               if anamnesis_result.get("expectations") is not None else "")
        if "alta" in _ex:
            family_attitude[22] = "1"
        elif "mediana" in _ex:
            family_attitude[23] = "1"
        elif "baja" in _ex:
            family_attitude[24] = "1"
        _env = (str(anamnesis_result.get("environment") or "").strip().lower()
               if anamnesis_result.get("environment") is not None else "")
        if "ambos" in _env:
            family_attitude[25] = "1"
        elif "físico" in _env or "fisico" in _env or "solo físico" in _env:
            family_attitude[26] = "1"
        elif "emocional" in _env or "solo emocional" in _env:
            family_attitude[27] = "1"
        final_comments = str(anamnesis_result.get("final_comments") or "").strip()
        if not current_level:
            current_level = course
        replacements = {
            "student_name": student_name, "birth_day": birth_day, "age": age_years, "month": age_months,
            "female": female, "male": male, "birth_country": birth_country, "address": address, "phone": phone,
            "mother_language": mother_language, "used_language": used_language, "course": course, "school": school,
            "ml_understand": ml_1, "ml_speak": ml_2, "ml_read": ml_3, "ml_write": ml_4,
            "ul_understand": ul_1, "ul_speak": ul_2, "ul_read": ul_3, "ul_write": ul_4,
            "interview_reason": interview_reason, "diagnosis_detail": diagnosis_detail, "dpy": dpy, "dpn": dpn,
            "bknormal": bknormal, "bkassisted": bkassisted, "bkforceps": bkforceps, "bkcesarean": bkcesarean,
            "bay": bay, "ban": ban, "fypcy": fypcy, "fypcn": fypcn, "fyvy": fyvy, "fyvn": fyvn,
            "desnutritiony": desnutritiony, "desnutritionn": desnutritionn, "obesityy": obesityy, "obesityn": obesityn,
            "highfevery": highfevery, "highfevern": highfevern, "seizuresy": seizuresy, "seizuresn": seizuresn,
            "hospitalizationsy": hospitalizationsy, "hospitalizationsn": hospitalizationsn, "injuy": injuy, "injun": injun,
            "iny": iny, "inn": inn, "ay": ay, "an": an, "riy": riy, "rin": rin, "encpy": encpy, "encpn": encpn,
            "mgy": mgy, "mgn": mgn, "oy": oy, "on": on, "otro": first_year_conditions_other_specify,
            "first_year_conditions_other_specify": first_year_conditions_other_specify,
            "birth_reason": birth_reason, "birth_weight": birth_weight, "birth_height": birth_height, "first_year_notes": first_year_notes,
            "dresses_alone": dresses_alone, "sits_alone": sits_alone, "head_control": head_control, "walks_without_support": walks_without_support,
            "first_words": first_words, "fiorst_words": first_words, "first_phrases": first_phrases,
            "control_sphincter_day": control_sphincter_day, "control_sphincter_night": control_sphincter_night,
            "bladder_sphincter_day": bladder_sphincter_day, "bladder_sphincter_night": bladder_sphincter_night,
            "sm_observations": sm_observations, "ma_1": ma_1, "ma_2": ma_2, "ma_3": ma_3, "ma_4": ma_4,
            "mt_1": mt_1, "mt_2": mt_2, "mt_3": mt_3, "mt_4": mt_4, "wsy": wsy, "wsn": wsn, "ffy": ffy, "ffn": ffn,
            "ldy": ldy, "ldn": ldn,
            "fgraby": fgraby, "fgrabn": fgrabn, "fgripy": fgripy, "fgripn": fgripn, "fpinchy": fpinchy, "fpinchn": fpinchn,
            "fdrawy": fdrawy, "fdrawn": fdrawn, "fwritey": fwritey, "fwriten": fwriten, "fthready": fthready, "fthreadn": fthreadn,
            **{f"vqy_{i+1}": vqy[i] for i in range(16)}, **{f"vqn_{i+1}": vqn[i] for i in range(16)},
            **{f"cqy_{i+1}": cqy[i] for i in range(8)}, **{f"cqn_{i+1}": cqn[i] for i in range(8)},
            **{f"cqy{i+1}": cqy[i] for i in range(8)}, **{f"cqn{i+1}": cqn[i] for i in range(8)},
            "dlq_1": dlq_1, "dlq_2": dlq_2, "dlq_3": dlq_3, "dlq_4": dlq_4, "dlq": dlq,
            **{f"cley_{i+1}": cley[i] for i in range(6)}, **{f"clen_{i+1}": clen[i] for i in range(6)},
            **{f"clcy_{i+1}": clcy[i] for i in range(8)}, **{f"clcn_{i+1}": clcn[i] for i in range(8)}, "clc": clc_text, "language_oral_loss": clc_text,
            **{f"dsy_{i+1}": dsy[i] for i in range(12)}, **{f"dsn_{i+1}": dsn[i] for i in range(12)},
            **{f"cshy_{i+1}": cshy[i] for i in range(11)}, **{f"cshn_{i+1}": cshn[i] for i in range(11)}, "csh": csh_text, "health_other_specify": csh_text,
            "family_medical_history": family_medical_history, "family_health_history": family_medical_history,
            "family_medical_observation": family_medical_observation, "family_health_observations": family_medical_observation,
            **{f"sq_{i+1}": sq[i] for i in range(6)}, "feed_1": feed_1, "feed_2": feed_2, "feed_3": feed_3, "feed_4": feed_4,
            "feed1": feed_1, "feed2": feed_2, "feed3": feed_3, "feed4": feed_4, "feed_other": feed_other_text,
            "weight_1": weight_1, "weight_2": weight_2, "weight_3": weight_3,
            "weight1": weight_1, "weight2": weight_2, "weight3": weight_3,
            "sleep_1": sleep_1, "sleep_2": sleep_2, "sleep_3": sleep_3,
            "sleep1": sleep_1, "sleep2": sleep_2, "sleep3": sleep_3, "sleep_time": sleep_time,
            "badsleep_1": badsleep_1, "badsleep_2": badsleep_2, "badsleep_3": badsleep_3, "badsleep_4": badsleep_4, "badsleep_5": badsleep_5,
            "badsleep1": badsleep_1, "badsleep2": badsleep_2, "badsleep3": badsleep_3, "badsleep4": badsleep_4, "badsleep5": badsleep_5,
            "howsleep1": howsleep1, "howsleep2": howsleep2, "howsleep": howsleep,
            "mood1": mood1, "mood2": mood2, "mood3": mood3, "mood4": mood4, "mood5": mood5, "mood6": mood6, "mood7": mood7, "mood8": mood8, "another_mood": another_mood,
            "enter_schooling_age": enter_schooling_age, "school_entry_age": enter_schooling_age,
            "kindergarten1": kindergarten1, "kindergarten2": kindergarten2,
            "school_assisted_number": school_assisted_number, "schools_count": school_assisted_number,
            "teaching1": teaching1, "teaching2": teaching2, "teaching3": teaching3, "why_change_of_school": why_change_of_school,
            "repeatedcourse1": repeatedcourse1, "repeatedcourse2": repeatedcourse2, "courses": courses, "repeated_courses": courses,
            "why_repeated": why_repeated, "repeated_reason": why_repeated,
            "current_level": current_level,
            **{f"current_situation{i+1}": current_situation[i] for i in range(14)},
            **{f"family_attitude{i+1}": family_attitude[i] for i in range(28)},
            "family_attitude_performance_reasons": family_attitude_performance_reasons,
            "family_attitude_response_difficulties_other": family_attitude_response_difficulties_other,
            "family_attitude_response_success_other": family_attitude_response_success_other,
            "family_attitude_rewards_other": family_attitude_rewards_other,
            "performance_reasons": family_attitude_performance_reasons,
            "response_difficulties_other": family_attitude_response_difficulties_other,
            "response_success_other": family_attitude_response_success_other,
            "rewards_other": family_attitude_rewards_other,
            "pediatry": spec_map["pediatry"], "kinesiology": spec_map["kinesiology"], "genetic": spec_map["genetic"], "neurology": spec_map["neurology"],
            "speechtherapy": spec_map["speechtherapy"], "another_diagnostic": spec_map["another_diagnostic"],
            "occupational_therapy": spec_map["occupational_therapy"], "educational_psychology": spec_map["educational_psychology"],
            "psychiatry": spec_map["psychiatry"], "psychology": spec_map["psychology"],
            "iidate_1": informant_data["date"][0], "iiname_1": informant_data["name"][0], "iirelation_1": informant_data["relation"][0], "iipresence_1": informant_data["presence"][0],
            "iidate_2": informant_data["date"][1], "iiname_2": informant_data["name"][1], "iirelation_2": informant_data["relation"][1], "iipresence_2": informant_data["presence"][1],
            "iidate_3": informant_data["date"][2], "iiname_3": informant_data["name"][2], "iirelation_3": informant_data["relation"][2], "iipresence_3": informant_data["presence"][2],
            "iidate_4": informant_data["date"][3], "iiname_4": informant_data["name"][3], "iirelation_4": informant_data["relation"][3], "iipresence_4": informant_data["presence"][3],
            "iindate_1": interviewer_data["date"][0], "iinname_1": interviewer_data["name"][0], "iinrol_1": interviewer_data["rol"][0],
            "iindate_2": interviewer_data["date"][1], "iinname_2": interviewer_data["name"][1], "iinrol_2": interviewer_data["rol"][1],
            "iindate_3": interviewer_data["date"][2], "iinname_3": interviewer_data["name"][2], "iinrol_3": interviewer_data["rol"][2],
            "iindate_4": interviewer_data["date"][3], "iinname_4": interviewer_data["name"][3], "iinrol_4": interviewer_data["rol"][3],
            **{f"fm_name_{i+1}": fm_data["name"][i] for i in range(8)}, **{f"fm_relation_{i+1}": fm_data["relation"][i] for i in range(8)},
            **{f"fm_age_{i+1}": fm_data["age"][i] for i in range(8)}, **{f"fm_schooling_{i+1}": fm_data["schooling"][i] for i in range(8)}, **{f"fm_occupation_{i+1}": fm_data["occupation"][i] for i in range(8)},
            "final_comments": final_comments,
        }
        template_path = Path("files/original_student_files") / "anamnesis_student.docx"
        if not template_path.exists():
            return {"status": "error", "message": "Template anamnesis_student.docx no encontrado", "status_code": 404}
        out_dir = Path("files/system/students")
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r'[^\w\s-]', '', student_name)[:30].strip() or "estudiante"
        out_file = out_dir / f"anamnesis_{safe_name}_{uuid.uuid4().hex[:8]}.docx"
        result = DocumentsClass.fill_docx_form(str(template_path), replacements, str(out_file))
        if result.get("status") == "error":
            return {"status": "error", "message": result.get("message", "Error generando DOCX"), "status_code": 500}
        return {"status": "success", "file_path": result["file_path"], "filename": result["filename"]}
    except Exception as e:
        return {"status": "error", "message": str(e), "status_code": 500}


def _split_course_activity_records_for_register_book(
    db: Session, course_id: int
) -> tuple[list[tuple[str, Any]], list, list, list]:
    """
    Libro de registro IV/V: lee tres tablas (sin columna section) y arma los tres bloques del Word.

    - course_activity_family    → _rafc_rows  → tags rafcf_* / rafcne_* …
    - course_activity_community → _tcee_rows → tags tcee*
    - course_activity_other     → _ar_rows   → tags arf_* / arn_* …

    _car_all: mezcla (etiqueta lógica, fila ORM) ordenada por fecha e id descendente (solo depuración/vista).
    """
    _rafc_rows = (
        db.query(CourseActivityFamilyModel)
        .filter(CourseActivityFamilyModel.course_id == course_id)
        .order_by(CourseActivityFamilyModel.date.desc(), CourseActivityFamilyModel.id.desc())
        .all()
    )
    _tcee_rows = (
        db.query(CourseActivityCommunityModel)
        .filter(CourseActivityCommunityModel.course_id == course_id)
        .order_by(CourseActivityCommunityModel.date.desc(), CourseActivityCommunityModel.id.desc())
        .all()
    )
    _ar_rows = (
        db.query(CourseActivityOtherModel)
        .filter(CourseActivityOtherModel.course_id == course_id)
        .order_by(CourseActivityOtherModel.date.desc(), CourseActivityOtherModel.id.desc())
        .all()
    )
    _car_all: list[tuple[str, Any]] = []
    for _rec in _rafc_rows:
        _car_all.append(("family", _rec))
    for _rec in _tcee_rows:
        _car_all.append(("community", _rec))
    for _rec in _ar_rows:
        _car_all.append(("other", _rec))
    _car_all.sort(
        key=lambda t: (t[1].date or date.min, t[1].id or 0),
        reverse=True,
    )
    return _car_all, _rafc_rows, _tcee_rows, _ar_rows


def _generate_register_book_impl(course_id: int, db: Session):
    """Lógica común para generar el libro de registro por course_id. Rellena regular, specialist, specialized_assistant y coordinadores (school, daem, support_networks)."""
    template_path = Path("files/original_student_files") / "register_book.docx"
    if not template_path.exists():
        return None, "Template register_book.docx no encontrado en files/original_student_files"
    replacements = {}
    for i in range(1, 5):
        replacements[f"regular_professional_full_name_{i}"] = ""
        replacements[f"regular_professional_subject_{i}"] = ""
        replacements[f"regular_professional_phone_{i}"] = ""
        replacements[f"regular_professional_email_{i}"] = ""
        replacements[f"specialist_professional_full_name_{i}"] = ""
        replacements[f"specialist_professional_subject_{i}"] = ""
        replacements[f"specialist_professional_phone_{i}"] = ""
        replacements[f"specialist_professional_email_{i}"] = ""
    for i in range(1, 4):
        replacements[f"specialized_assistant_professional_full_name_{i}"] = ""
        replacements[f"specialized_assistant_professional_subject_{i}"] = ""
        replacements[f"specialized_assistant_professional_phone_{i}"] = ""
        replacements[f"specialized_assistant_professional_email_{i}"] = ""
    replacements["school_coordinator_full_name"] = ""
    replacements["school_coordinator_email"] = ""
    replacements["school_coordinator_phone"] = ""
    replacements["daem_coordinator_full_name"] = ""
    replacements["daem_coordinator_email"] = ""
    replacements["daem_coordinator_phone"] = ""
    replacements["support_networks_coordinator_full_name"] = ""
    replacements["support_networks_coordinator_email"] = ""
    replacements["support_networks_coordinator_phone"] = ""
    # Panorama del curso (documento: Estilos y modos / Fortalezas / Necesidades de apoyo)
    replacements["emac"] = ""
    replacements["fc"] = ""
    replacements["nac"] = ""
    replacements["EMAC"] = ""
    replacements["FC"] = ""
    replacements["NAC"] = ""
    # Colaboración: Estrategias y/o acciones (sección c) — satc_1..6
    for i in range(1, 7):
        replacements[f"satc_{i}"] = ""
    # II b) Registros dinámicos: cada registro = rarpo_k + 11 filas (rarpf/rarphp/rarpad/rarpnfd). Máx. configurable.
    _RB_ROWS_PER_REGISTER = 11
    _RB_MAX_REGISTERS = 20
    _RB_MAX_ACTIVITY_ROWS = _RB_ROWS_PER_REGISTER * _RB_MAX_REGISTERS
    for _rk in range(1, _RB_MAX_REGISTERS + 1):
        replacements[f"rarpo_{_rk}"] = ""
        replacements[f"rarpas_{_rk}"] = ""

    ds_row = (
        db.query(DiversifiedStrategyModel)
        .filter(DiversifiedStrategyModel.course_id == course_id)
        .order_by(DiversifiedStrategyModel.id.desc())
        .first()
    )
    if ds_row:
        emac_val = (ds_row.planning_learning_styles or "").strip()
        fc_val = (ds_row.planning_strengths or "").strip()
        nac_val = (ds_row.planning_support_needs or "").strip()
        replacements["emac"] = emac_val
        replacements["fc"] = fc_val
        replacements["nac"] = nac_val
        replacements["EMAC"] = emac_val
        replacements["FC"] = fc_val
        replacements["NAC"] = nac_val

    cw_row = (
        db.query(CollaborativeWorkModel)
        .filter(CollaborativeWorkModel.course_id == course_id)
        .order_by(CollaborativeWorkModel.id.desc())
        .first()
    )
    if cw_row:
        replacements["satc_1"] = (cw_row.planning_collab_co_teaching or "").strip()
        replacements["satc_2"] = (cw_row.planning_collab_assistants or "").strip()
        replacements["satc_3"] = (cw_row.planning_collab_students or "").strip()
        replacements["satc_4"] = (cw_row.planning_collab_family or "").strip()
        replacements["satc_5"] = (cw_row.planning_collab_community or "").strip()
        replacements["satc_6"] = (cw_row.planning_observations or "").strip()
    # II b) Registro por asignatura (mismas pestañas que la UI): observaciones y tabla por subject_id — no usar collaborative_works para rarpo_*
    _obs_sids = [
        t[0]
        for t in db.query(CourseTeacherRecordObservationModel.subject_id)
        .filter(CourseTeacherRecordObservationModel.course_id == course_id)
        .distinct()
        .all()
    ]
    _act_sids = [
        t[0]
        for t in db.query(CourseTeacherRecordActivityModel.subject_id)
        .filter(CourseTeacherRecordActivityModel.course_id == course_id)
        .distinct()
        .all()
    ]
    # Orden: por primer registro (id mínimo) de actividad u observación en el curso por asignatura — suele coincidir con pestañas; no alfabético.
    _rb_sid_set = set(_obs_sids) | set(_act_sids)
    _rb_scored = []
    for _sid in _rb_sid_set:
        _min_a = (
            db.query(func.min(CourseTeacherRecordActivityModel.id))
            .filter(
                CourseTeacherRecordActivityModel.course_id == course_id,
                CourseTeacherRecordActivityModel.subject_id == _sid,
            )
            .scalar()
        )
        _min_o = (
            db.query(func.min(CourseTeacherRecordObservationModel.id))
            .filter(
                CourseTeacherRecordObservationModel.course_id == course_id,
                CourseTeacherRecordObservationModel.subject_id == _sid,
            )
            .scalar()
        )
        _cands = [x for x in (_min_a, _min_o) if x is not None]
        _rank = min(_cands) if _cands else 10**12
        _rb_scored.append((_rank, _sid))
    _rb_scored.sort(key=lambda x: (x[0], x[1]))
    _rb_subject_ids = [x[1] for x in _rb_scored]
    _rb_subject_blocks = []
    for _sid in _rb_subject_ids:
        _sj = db.query(SubjectModel).filter(SubjectModel.id == _sid).first()
        _slbl = (_sj.subject or "").strip() if _sj else str(_sid)
        _rb_subject_blocks.append((_sid, _slbl))
    for _idx, (_sid, _slabel) in enumerate(_rb_subject_blocks[:_RB_MAX_REGISTERS]):
        _k = _idx + 1
        replacements[f"rarpas_{_k}"] = _slabel
        _obs_row = (
            db.query(CourseTeacherRecordObservationModel)
            .filter(
                CourseTeacherRecordObservationModel.course_id == course_id,
                CourseTeacherRecordObservationModel.subject_id == _sid,
            )
            .first()
        )
        if _obs_row:
            replacements[f"rarpo_{_k}"] = (_obs_row.observations or "").strip()

    # Tabla: por cada asignatura, hasta 11 filas; bloque 1 → filas 1–11, bloque 2 → 12–22, … (alineado con rarpo_k / rarpas_k)
    def _register_book_teacher_names_line(raw) -> str:
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return ""
        if isinstance(raw, list):
            parts = []
            for item in raw:
                if isinstance(item, dict):
                    n = (item.get("name") or item.get("nombre") or "").strip()
                    if n:
                        parts.append(n)
                elif item:
                    parts.append(str(item).strip())
            return ", ".join(parts)
        try:
            data = json.loads(raw) if isinstance(raw, str) else None
            if isinstance(data, list):
                return _register_book_teacher_names_line(data)
        except (json.JSONDecodeError, TypeError):
            pass
        return str(raw).strip()

    for _ri in range(1, _RB_MAX_ACTIVITY_ROWS + 1):
        replacements[f"rarpf_{_ri}"] = ""
        replacements[f"rarphp_{_ri}"] = ""
        replacements[f"rarpad_{_ri}"] = ""
        replacements[f"rarpnfd_{_ri}"] = ""
    for _bidx, (_sid, _slabel) in enumerate(_rb_subject_blocks[:_RB_MAX_REGISTERS]):
        _base = _bidx * _RB_ROWS_PER_REGISTER
        _cta_sub = (
            db.query(CourseTeacherRecordActivityModel)
            .filter(
                CourseTeacherRecordActivityModel.course_id == course_id,
                CourseTeacherRecordActivityModel.subject_id == _sid,
            )
            .order_by(CourseTeacherRecordActivityModel.date.asc(), CourseTeacherRecordActivityModel.id.asc())
            .limit(_RB_ROWS_PER_REGISTER)
            .all()
        )
        for _j, _cta in enumerate(_cta_sub):
            _n = _base + _j + 1
            if _n > _RB_MAX_ACTIVITY_ROWS:
                break
            if _cta.date:
                replacements[f"rarpf_{_n}"] = _cta.date.strftime("%d/%m/%Y")
            _ph = getattr(_cta, "pedagogical_hours", None)
            if _ph is not None:
                replacements[f"rarphp_{_n}"] = str(_ph).strip()
            replacements[f"rarpad_{_n}"] = (getattr(_cta, "description", None) or "").strip()
            replacements[f"rarpnfd_{_n}"] = _register_book_teacher_names_line(getattr(_cta, "teacher_names", None))

    # b) Organización de los apoyos: support_organizations (hasta 13 filas por curso)
    for i in range(1, 14):
        replacements[f"oaaa_{i}"] = ""
        replacements[f"haar_{i}"] = ""
        replacements[f"hafa_{i}"] = ""
        replacements[f"tae_{i}"] = ""
    sup_org_rows = (
        db.query(SupportOrganizationModel, SubjectModel)
        .outerjoin(SubjectModel, SupportOrganizationModel.subject_id == SubjectModel.id)
        .filter(
            SupportOrganizationModel.course_id == course_id,
            SupportOrganizationModel.deleted_date.is_(None),
        )
        .order_by(SupportOrganizationModel.id)
        .limit(13)
        .all()
    )
    for idx, (sup, subj) in enumerate(sup_org_rows):
        if idx >= 13:
            break
        n = idx + 1
        ambito = ""
        if subj and (subj.subject or "").strip():
            ambito = (subj.subject or "").strip()
        elif getattr(sup, "subject_id", None):
            ambito = str(sup.subject_id).strip()
        replacements[f"oaaa_{n}"] = ambito
        replacements[f"haar_{n}"] = (sup.hours_support_regular_classroom or "").strip()
        replacements[f"hafa_{n}"] = (sup.hours_support_outside_classroom or "").strip()
        replacements[f"tae_{n}"] = (sup.specialized_support_types or "").strip()

    # Días de la semana por mes para todo el año (january..december),
    # cubriendo toda la semana (monday..sunday) desde meeting_schedualings.
    _weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    _months = [
        (1, "january"),
        (2, "february"),
        (3, "march"),
        (4, "april"),
        (5, "may"),
        (6, "june"),
        (7, "july"),
        (8, "august"),
        (9, "september"),
        (10, "october"),
        (11, "november"),
        (12, "december"),
    ]
    for _, month_name in _months:
        for wd in _weekdays:
            replacements[f"{month_name}_{wd}_date"] = ""
            replacements[f"{month_name}_{wd}_time"] = ""
    def _fill_slot(month_name: str, wd_name: str, row: MeetingSchedulalingModel):
        replacements[f"{month_name}_{wd_name}_date"] = row.meeting_date.strftime("%d/%m/%Y")
        replacements[f"{month_name}_{wd_name}_time"] = (row.meeting_time or "").strip()

    # Periodo 1 -> enero..julio (por mes real)
    meetings_p1 = (
        db.query(MeetingSchedulalingModel)
        .filter(
            MeetingSchedulalingModel.course_id == course_id,
            MeetingSchedulalingModel.period_id == 1,
            MeetingSchedulalingModel.meeting_date.isnot(None),
            MeetingSchedulalingModel.deleted_date.is_(None),
        )
        .order_by(MeetingSchedulalingModel.meeting_date)
        .all()
    )
    for row in meetings_p1:
        d = row.meeting_date
        if not d or not hasattr(d, "month"):
            continue
        if d.month not in (1, 2, 3, 4, 5, 6, 7):
            continue
        wd_idx = d.weekday()
        if wd_idx > 6:
            continue
        month_name = next((m[1] for m in _months if m[0] == d.month), None)
        if not month_name:
            continue
        _fill_slot(month_name, _weekdays[wd_idx], row)

    # Periodo 2 -> agosto..diciembre.
    meetings_p2 = (
        db.query(MeetingSchedulalingModel)
        .filter(
            MeetingSchedulalingModel.course_id == course_id,
            MeetingSchedulalingModel.period_id == 2,
            MeetingSchedulalingModel.meeting_date.isnot(None),
            MeetingSchedulalingModel.deleted_date.is_(None),
        )
        .order_by(MeetingSchedulalingModel.meeting_date)
        .all()
    )
    unmatched_p2 = []
    for row in meetings_p2:
        d = row.meeting_date
        if not d or not hasattr(d, "month"):
            continue
        wd_idx = d.weekday()
        if wd_idx > 6:
            continue
        if d.month in (8, 9, 10, 11, 12):
            month_name = next((m[1] for m in _months if m[0] == d.month), None)
            if month_name:
                _fill_slot(month_name, _weekdays[wd_idx], row)
        else:
            # Fallback: si en periodo 2 guardaron fechas fuera de agosto..diciembre,
            # se ubican en el primer mes disponible de agosto..diciembre para ese día.
            unmatched_p2.append((row, wd_idx))

    _months_p2 = ["august", "september", "october", "november", "december"]
    for row, wd_idx in unmatched_p2:
        wd_name = _weekdays[wd_idx]
        for mname in _months_p2:
            if not replacements.get(f"{mname}_{wd_name}_date"):
                _fill_slot(mname, wd_name, row)
                break
    # Profesores regulares (teacher_type_id=1)
    ptc_regular = (
        db.query(ProfessionalTeachingCourseModel, ProfessionalModel)
        .join(ProfessionalModel, ProfessionalTeachingCourseModel.professional_id == ProfessionalModel.id)
        .filter(
            ProfessionalTeachingCourseModel.course_id == course_id,
            ProfessionalTeachingCourseModel.teacher_type_id == 1,
            ProfessionalTeachingCourseModel.deleted_status_id == 0,
        )
        .order_by(ProfessionalTeachingCourseModel.id)
        .limit(4)
        .all()
    )
    for idx, (ptc, prof) in enumerate(ptc_regular):
        if idx >= 4:
            break
        i = idx + 1
        full_name = f"{prof.names or ''} {prof.lastnames or ''}".strip()
        replacements[f"regular_professional_full_name_{i}"] = full_name
        replacements[f"regular_professional_subject_{i}"] = (ptc.subject or "").strip()
        replacements[f"regular_professional_phone_{i}"] = (prof.phone or "").strip()
        replacements[f"regular_professional_email_{i}"] = (prof.email or "").strip()
    # Profesionales especialistas (teacher_type_id=2)
    ptc_specialist = (
        db.query(ProfessionalTeachingCourseModel, ProfessionalModel)
        .join(ProfessionalModel, ProfessionalTeachingCourseModel.professional_id == ProfessionalModel.id)
        .filter(
            ProfessionalTeachingCourseModel.course_id == course_id,
            ProfessionalTeachingCourseModel.teacher_type_id == 2,
            ProfessionalTeachingCourseModel.deleted_status_id == 0,
        )
        .order_by(ProfessionalTeachingCourseModel.id)
        .limit(4)
        .all()
    )
    for idx, (ptc, prof) in enumerate(ptc_specialist):
        if idx >= 4:
            break
        i = idx + 1
        full_name = f"{prof.names or ''} {prof.lastnames or ''}".strip()
        replacements[f"specialist_professional_full_name_{i}"] = full_name
        replacements[f"specialist_professional_subject_{i}"] = (ptc.subject or "").strip()
        replacements[f"specialist_professional_phone_{i}"] = (prof.phone or "").strip()
        replacements[f"specialist_professional_email_{i}"] = (prof.email or "").strip()
    # Asistentes especializados (teacher_type_id=3), del 1 al 3
    ptc_assistant = (
        db.query(ProfessionalTeachingCourseModel, ProfessionalModel)
        .join(ProfessionalModel, ProfessionalTeachingCourseModel.professional_id == ProfessionalModel.id)
        .filter(
            ProfessionalTeachingCourseModel.course_id == course_id,
            ProfessionalTeachingCourseModel.teacher_type_id == 3,
            ProfessionalTeachingCourseModel.deleted_status_id == 0,
        )
        .order_by(ProfessionalTeachingCourseModel.id)
        .limit(3)
        .all()
    )
    for idx, (ptc, prof) in enumerate(ptc_assistant):
        if idx >= 3:
            break
        i = idx + 1
        full_name = f"{prof.names or ''} {prof.lastnames or ''}".strip()
        replacements[f"specialized_assistant_professional_full_name_{i}"] = full_name
        replacements[f"specialized_assistant_professional_subject_{i}"] = (ptc.subject or "").strip()
        replacements[f"specialized_assistant_professional_phone_{i}"] = (prof.phone or "").strip()
        replacements[f"specialized_assistant_professional_email_{i}"] = (prof.email or "").strip()
    # Coordinadores: school (coordinator_type_id=1), daem (2), support_networks (3)
    for coordinator_type_id, prefix in [(1, "school"), (2, "daem"), (3, "support_networks")]:
        coord = (
            db.query(CoordinatorsCourseModel, ProfessionalModel)
            .join(ProfessionalModel, CoordinatorsCourseModel.professional_id == ProfessionalModel.id)
            .filter(
                CoordinatorsCourseModel.course_id == course_id,
                CoordinatorsCourseModel.coordinator_type_id == coordinator_type_id,
                CoordinatorsCourseModel.deleted_date.is_(None),
            )
            .order_by(CoordinatorsCourseModel.id)
            .first()
        )
        if coord:
            cc, prof = coord
            full_name = f"{prof.names or ''} {prof.lastnames or ''}".strip()
            replacements[f"{prefix}_coordinator_full_name"] = full_name
            replacements[f"{prefix}_coordinator_email"] = (cc.email or prof.email or "").strip()
            replacements[f"{prefix}_coordinator_phone"] = (cc.phone or prof.phone or "").strip()
    # Reuniones 1 a 10:
    # - 1..5  => periodo 1
    # - 6..10 => periodo 2
    # meeting_schedualing_registers_professionals + meeting_schedualing_agreements.
    for i in range(1, 11):
        replacements[f"reunion_date_{i}"] = ""
        replacements[f"reunion_attendees_{i}"] = ""
        replacements[f"reunion_agreements_{i}"] = ""

    meetings_for_reunion_p1 = (
        db.query(MeetingSchedulalingModel)
        .filter(
            MeetingSchedulalingModel.course_id == course_id,
            MeetingSchedulalingModel.period_id == 1,
            MeetingSchedulalingModel.deleted_date.is_(None),
        )
        .order_by(MeetingSchedulalingModel.meeting_date)
        .limit(5)
        .all()
    )

    meetings_for_reunion_p2 = (
        db.query(MeetingSchedulalingModel)
        .filter(
            MeetingSchedulalingModel.course_id == course_id,
            MeetingSchedulalingModel.period_id == 2,
            MeetingSchedulalingModel.deleted_date.is_(None),
        )
        .order_by(MeetingSchedulalingModel.meeting_date)
        .limit(5)
        .all()
    )

    def _fill_reunion_slot(i: int, meeting: MeetingSchedulalingModel):
        if meeting.meeting_date:
            replacements[f"reunion_date_{i}"] = meeting.meeting_date.strftime("%d/%m/%Y")
        # Asistentes: meeting_schedualing_registers_professionals con meeting_schedualing_register_id = meeting.id, join professionals
        reg_rows = (
            db.query(MeetingSchedualingRegisterProfessionalModel)
            .filter(
                MeetingSchedualingRegisterProfessionalModel.meeting_schedualing_register_id == meeting.id,
                MeetingSchedualingRegisterProfessionalModel.deleted_date.is_(None),
            )
            .all()
        )
        names = []
        for rp in reg_rows:
            fn = ""
            prof = db.query(ProfessionalModel).filter(ProfessionalModel.id == rp.professional_id).first()
            if prof:
                fn = f"{prof.names or ''} {prof.lastnames or ''}".strip()
            else:
                usr = db.query(UserModel).filter(UserModel.id == rp.professional_id).first()
                if usr:
                    fn = (usr.full_name or "").strip()
            if fn:
                names.append(fn)
        replacements[f"reunion_attendees_{i}"] = ", ".join(names)
        # Acuerdos: meeting_schedualing_agreements por meeting_schedualing_id
        agreements_rows = (
            db.query(MeetingSchedualingAgreementModel)
            .filter(
                MeetingSchedualingAgreementModel.meeting_schedualing_id == meeting.id,
                MeetingSchedualingAgreementModel.deleted_date.is_(None),
            )
            .all()
        )
        agreements_text = "; ".join((r.agreements or "").strip() for r in agreements_rows if (r.agreements or "").strip())
        replacements[f"reunion_agreements_{i}"] = agreements_text

    for idx, meeting in enumerate(meetings_for_reunion_p1):
        if idx >= 5:
            break
        _fill_reunion_slot(idx + 1, meeting)

    for idx, meeting in enumerate(meetings_for_reunion_p2):
        if idx >= 5:
            break
        _fill_reunion_slot(idx + 6, meeting)

    # a) Estrategias diversidad en el aula común: columna 1 — cseacpea_1..3 (casillas), cseacpea_4 (Otro, texto)
    replacements["cseacpea_1"] = ""
    replacements["cseacpea_2"] = ""
    replacements["cseacpea_3"] = ""
    replacements["cseacpea_4"] = ""
    div_criteria = (
        db.query(DiversityCriterionModel)
        .filter(DiversityCriterionModel.deleted_date.is_(None))
        .order_by(DiversityCriterionModel.sort_order)
        .all()
    )
    div_responses = (
        db.query(CourseDiversityResponseModel)
        .filter(
            CourseDiversityResponseModel.course_id == course_id,
            CourseDiversityResponseModel.deleted_date.is_(None),
        )
        .all()
    )
    _div_by_cid = {r.diversity_criterion_id: r for r in div_responses}
    for i in range(3):
        if i >= len(div_criteria):
            break
        c = div_criteria[i]
        r = _div_by_cid.get(c.id)
        replacements[f"cseacpea_{i + 1}"] = "1" if r and getattr(r, "criterion_selected", 0) else ""
    _otro_crit = next(
        (c for c in div_criteria if (c.key or "").strip().lower() in ("otro", "other", "otra")),
        None,
    )
    if _otro_crit is None and len(div_criteria) >= 4:
        _otro_crit = div_criteria[3]
    if _otro_crit:
        _r_otro = _div_by_cid.get(_otro_crit.id)
        if _r_otro:
            replacements["cseacpea_4"] = (_r_otro.how_text or "").strip()

    # a) columna 2 — cseacpeas_1..8 (casillas), cseacpeas_9 (Otros)
    for _i in range(1, 10):
        replacements[f"cseacpeas_{_i}"] = ""
    _strategy_opts_ordered = (
        db.query(DiversityStrategyOptionModel)
        .join(
            DiversityCriterionModel,
            DiversityStrategyOptionModel.diversity_criterion_id == DiversityCriterionModel.id,
        )
        .filter(
            DiversityStrategyOptionModel.deleted_date.is_(None),
            DiversityCriterionModel.deleted_date.is_(None),
        )
        .order_by(DiversityCriterionModel.sort_order, DiversityStrategyOptionModel.sort_order)
        .all()
    )
    _otro_strat = next(
        (o for o in _strategy_opts_ordered if "otro" in (o.label or "").lower()),
        None,
    )
    _opts_col2_1_8 = [o for o in _strategy_opts_ordered if _otro_strat is None or o.id != _otro_strat.id][:8]
    for _idx, _opt in enumerate(_opts_col2_1_8):
        _r = _div_by_cid.get(_opt.diversity_criterion_id)
        replacements[f"cseacpeas_{_idx + 1}"] = (
            "1"
            if _r
            and getattr(_r, "criterion_selected", 0)
            and getattr(_r, "diversity_strategy_option_id", None) == _opt.id
            else ""
        )
    _opt_otros_col2 = _otro_strat
    if _opt_otros_col2 is None and len(_strategy_opts_ordered) >= 9:
        _opt_otros_col2 = _strategy_opts_ordered[8]
    if _opt_otros_col2:
        _r9 = _div_by_cid.get(_opt_otros_col2.diversity_criterion_id)
        replacements["cseacpeas_9"] = (
            "1"
            if _r9
            and getattr(_r9, "criterion_selected", 0)
            and getattr(_r9, "diversity_strategy_option_id", None) == _opt_otros_col2.id
            else ""
        )

    # a) columna 3 — ¿Cómo? — csmafa_1..9
    for _i in range(1, 10):
        replacements[f"csmafa_{_i}"] = ""
    for _i in range(3):
        if _i >= len(div_criteria):
            break
        _c = div_criteria[_i]
        _r = _div_by_cid.get(_c.id)
        if _r:
            replacements[f"csmafa_{_i + 1}"] = (_r.how_text or "").strip()
    if _otro_crit:
        _r_o = _div_by_cid.get(_otro_crit.id)
        if _r_o:
            replacements["csmafa_4"] = (_r_o.how_text or "").strip()
    _adj_aspects = (
        db.query(AdjustmentAspectModel)
        .filter(AdjustmentAspectModel.deleted_date.is_(None))
        .order_by(AdjustmentAspectModel.sort_order)
        .all()
    )
    _adj_rows = (
        db.query(CourseAdjustmentModel)
        .filter(
            CourseAdjustmentModel.course_id == course_id,
            CourseAdjustmentModel.deleted_date.is_(None),
        )
        .all()
    )
    _adj_by_asp = {a.adjustment_aspect_id: a for a in _adj_rows}

    def _csmafa_adj_value(_asp_idx: int) -> str:
        if _asp_idx >= len(_adj_aspects):
            return ""
        _adj = _adj_by_asp.get(_adj_aspects[_asp_idx].id)
        if not _adj:
            return ""
        return (getattr(_adj, "value", None) or "").strip()

    for _j in range(3):
        replacements[f"csmafa_{5 + _j}"] = _csmafa_adj_value(_j)
    _asp_otro_adj = next(
        (a for a in _adj_aspects if "otro" in (a.key or "").lower()),
        _adj_aspects[3] if len(_adj_aspects) >= 4 else None,
    )
    # Ajustes — segunda columna (casillas) — ea_1..3 (materiales / tiempo / tarea), ea_4 (Otro)
    replacements["ea_1"] = ""
    replacements["ea_2"] = ""
    replacements["ea_3"] = ""
    replacements["ea_4"] = ""
    _aspects_ea123 = [a for a in _adj_aspects if _asp_otro_adj is None or a.id != _asp_otro_adj.id][:3]
    for _ea_i, _ea_asp in enumerate(_aspects_ea123):
        _ea_row = _adj_by_asp.get(_ea_asp.id)
        replacements[f"ea_{_ea_i + 1}"] = "1" if _ea_row else ""
    if _asp_otro_adj:
        replacements["ea_4"] = "1" if _adj_by_asp.get(_asp_otro_adj.id) else ""

    if _asp_otro_adj:
        _ad8 = _adj_by_asp.get(_asp_otro_adj.id)
        if _ad8:
            _v8 = (getattr(_ad8, "value", None) or "").strip()
            _o8 = (getattr(_ad8, "other_aspect_text", None) or "").strip()
            replacements["csmafa_8"] = " ".join(x for x in (_v8, _o8) if x).strip()
    _div_obs = (
        db.query(CourseDiversityObservationModel)
        .filter(CourseDiversityObservationModel.course_id == course_id)
        .first()
    )
    if _div_obs and (_div_obs.observations or "").strip():
        replacements["csmafa_9"] = (_div_obs.observations or "").strip()

    # a) columna 4 — ¿A quiénes? — qse_1..9 (nombres de estudiantes)
    def _qse_student_names_line(_sids: list) -> str:
        if not _sids:
            return ""
        _parts: list = []
        for _sid in _sids:
            if not _sid:
                continue
            _p = (
                db.query(StudentPersonalInfoModel)
                .filter(StudentPersonalInfoModel.student_id == _sid)
                .first()
            )
            if _p:
                _fn = f"{_p.names or ''} {_p.father_lastname or ''} {_p.mother_lastname or ''}".strip()
                if _fn:
                    _parts.append(_fn)
        return ", ".join(_parts)

    def _qse_sids_div_resp(_resp_id: int | None) -> list:
        if not _resp_id:
            return []
        return [
            t[0]
            for t in db.query(CourseDiversityResponseStudentModel.student_id)
            .filter(CourseDiversityResponseStudentModel.course_diversity_response_id == _resp_id)
            .all()
        ]

    def _qse_sids_adj(_adj_id: int | None) -> list:
        if not _adj_id:
            return []
        return [
            t[0]
            for t in db.query(CourseAdjustmentStudentModel.student_id)
            .filter(CourseAdjustmentStudentModel.course_adjustment_id == _adj_id)
            .all()
        ]

    for _qi in range(1, 10):
        replacements[f"qse_{_qi}"] = ""
    for _qi in range(3):
        if _qi >= len(div_criteria):
            break
        _cr = _div_by_cid.get(div_criteria[_qi].id)
        if _cr:
            replacements[f"qse_{_qi + 1}"] = _qse_student_names_line(_qse_sids_div_resp(_cr.id))
    if _otro_crit:
        _cr_o = _div_by_cid.get(_otro_crit.id)
        if _cr_o:
            replacements["qse_4"] = _qse_student_names_line(_qse_sids_div_resp(_cr_o.id))
    for _qj in range(3):
        if _qj >= len(_adj_aspects):
            break
        _adj_q = _adj_by_asp.get(_adj_aspects[_qj].id)
        if _adj_q:
            replacements[f"qse_{5 + _qj}"] = _qse_student_names_line(_qse_sids_adj(_adj_q.id))
    if _asp_otro_adj:
        _ad_q8 = _adj_by_asp.get(_asp_otro_adj.id)
        if _ad_q8:
            replacements["qse_8"] = _qse_student_names_line(_qse_sids_adj(_ad_q8.id))
    _seen_qse = set()
    _qse_course_sids: list = []
    for (_qsid,) in (
        db.query(StudentAcademicInfoModel.student_id)
        .filter(StudentAcademicInfoModel.course_id == course_id)
        .all()
    ):
        if _qsid and _qsid not in _seen_qse:
            _seen_qse.add(_qsid)
            _qse_course_sids.append(_qsid)
    replacements["qse_9"] = _qse_student_names_line(_qse_course_sids)
    # Fila "Otras estrategias y criterios": 1ª columna = osc_1, 2ª columna = osce_1
    replacements["osc_1"] = replacements["csmafa_9"]
    replacements["osce_1"] = replacements["qse_9"]
    # Campo general OBSERVACIONES (mismo texto que observaciones de diversidad del curso)
    replacements["edo_1"] = replacements["csmafa_9"]

    # 2. Registro de apoyos (course_record_support + interventions) — raegee_*, raegeop_*, raegef_*, …
    _RAEG_MAX_BLOCKS = 30
    _RAEG_MAX_ROWS = 25
    for _bb in range(1, _RAEG_MAX_BLOCKS + 1):
        replacements[f"raegee_{_bb}"] = ""
        replacements[f"raegeoa_{_bb}"] = ""
    replacements["raegeop_1_1"] = ""
    for _bb in range(2, _RAEG_MAX_BLOCKS + 1):
        replacements[f"raegeop_{_bb}_1"] = ""
    for _bb in range(1, _RAEG_MAX_BLOCKS + 1):
        for _br in range(1, _RAEG_MAX_ROWS + 1):
            if _bb == 1:
                replacements[f"raegef_1_{_br}"] = ""
                replacements[f"raegel_1_{_br}"] = ""
                replacements[f"raegear_1_{_br}"] = ""
                replacements[f"raegep_1_{_br}"] = ""
            else:
                replacements[f"raegef_{_bb}_{_br}"] = ""
                replacements[f"raegel_{_bb}_{_br}"] = ""
                replacements[f"raegear_{_bb}_{_br}"] = ""
                replacements[f"raegep_{_bb}_{_br}"] = ""

    _raeg_blocks: list = []
    _support_areas_raeg = (
        db.query(SupportAreaModel)
        .filter(SupportAreaModel.deleted_date.is_(None))
        .order_by(SupportAreaModel.support_area.asc())
        .all()
    )
    for _sa in _support_areas_raeg:
        _rec_cr = (
            db.query(CourseRecordSupportModel)
            .filter(
                CourseRecordSupportModel.course_id == course_id,
                CourseRecordSupportModel.support_area_id == _sa.id,
            )
            .first()
        )
        _stids_cr: list = []
        if _rec_cr:
            _stids_cr = [
                t[0]
                for t in db.query(CourseRecordSupportStudentModel.student_id)
                .filter(CourseRecordSupportStudentModel.course_record_support_id == _rec_cr.id)
                .all()
            ]
        _intvs_cr = (
            db.query(CourseRecordSupportInterventionModel)
            .filter(
                CourseRecordSupportInterventionModel.course_id == course_id,
                CourseRecordSupportInterventionModel.support_area_id == _sa.id,
            )
            .order_by(CourseRecordSupportInterventionModel.date.asc(), CourseRecordSupportInterventionModel.id.asc())
            .all()
        )
        _obj_cr = ((_rec_cr.learning_objectives or "").strip()) if _rec_cr else ""
        if not _stids_cr and not _intvs_cr and not _obj_cr:
            continue
        _raeg_blocks.append(
            {
                "student_ids": _stids_cr,
                "objectives": _obj_cr,
                "interventions": _intvs_cr,
            }
        )
    if len(_raeg_blocks) > _RAEG_MAX_BLOCKS:
        logger.warning(
            "register_book: se omiten registros de apoyos más allá de %s áreas",
            _RAEG_MAX_BLOCKS,
        )
        _raeg_blocks = _raeg_blocks[:_RAEG_MAX_BLOCKS]

    _n_raeg_blocks = max(1, len(_raeg_blocks))

    def _raeg_fmt_date(_d) -> str:
        if _d is None:
            return ""
        if hasattr(_d, "strftime"):
            return _d.strftime("%d/%m/%Y")
        return str(_d)

    _raeg_pid = set()
    for _blk in _raeg_blocks:
        for _iv in _blk["interventions"]:
            if getattr(_iv, "professional_id", None):
                _raeg_pid.add(_iv.professional_id)
    _raeg_prof_names: dict = {}
    if _raeg_pid:
        for _p in db.query(ProfessionalModel).filter(ProfessionalModel.id.in_(_raeg_pid)).all():
            _nm = f"{getattr(_p, 'names', '') or ''} {getattr(_p, 'lastnames', '') or ''}".strip()
            _raeg_prof_names[_p.id] = _nm or getattr(_p, "name", None) or str(_p.id)

    for _bi, _blk in enumerate(_raeg_blocks, start=1):
        replacements[f"raegee_{_bi}"] = _qse_student_names_line(_blk["student_ids"])
        if _bi == 1:
            replacements["raegeop_1_1"] = _blk["objectives"]
        else:
            replacements[f"raegeop_{_bi}_1"] = _blk["objectives"]
        _ints = _blk["interventions"]
        _fh = _ints[0].pedagogical_hours if _ints else None
        replacements[f"raegeoa_{_bi}"] = str(_fh).strip() if _fh is not None else ""
        for _ri, _iv in enumerate(_ints, start=1):
            if _ri > _RAEG_MAX_ROWS:
                break
            _act = (_iv.activities_description or "").strip()
            _pn = _raeg_prof_names.get(_iv.professional_id) if _iv.professional_id else ""
            if _bi == 1:
                replacements[f"raegef_1_{_ri}"] = _raeg_fmt_date(_iv.date)
                replacements[f"raegel_1_{_ri}"] = (_iv.place or "").strip()
                replacements[f"raegear_1_{_ri}"] = _act
                replacements[f"raegep_1_{_ri}"] = _pn
            else:
                replacements[f"raegef_{_bi}_{_ri}"] = _raeg_fmt_date(_iv.date)
                replacements[f"raegel_{_bi}_{_ri}"] = (_iv.place or "").strip()
                replacements[f"raegear_{_bi}_{_ri}"] = _act
                replacements[f"raegep_{_bi}_{_ri}"] = _pn

    # 3. Registro de logros de aprendizaje — rlane_1_*, rllr_1_*, rlcs_1_*
    _RLA_MAX_ROWS = 50
    for _r in range(1, _RLA_MAX_ROWS + 1):
        replacements[f"rlane_1_{_r}"] = ""
        replacements[f"rllr_1_{_r}"] = ""
        replacements[f"rlcs_1_{_r}"] = ""
    _la_rows = (
        db.query(CourseLearningAchievementModel)
        .filter(CourseLearningAchievementModel.course_id == course_id)
        .order_by(
            CourseLearningAchievementModel.period_id.asc(),
            CourseLearningAchievementModel.student_id.asc(),
            CourseLearningAchievementModel.id.asc(),
        )
        .all()
    )
    if len(_la_rows) > _RLA_MAX_ROWS:
        logger.warning(
            "register_book: se omiten logros de aprendizaje más allá de %s filas",
            _RLA_MAX_ROWS,
        )
        _la_rows = _la_rows[:_RLA_MAX_ROWS]
    # Filas donde empieza un período distinto al anterior → espacio superior en el DOCX (sin filas vacías)
    _rla_margin_top_rows: list[int] = []
    for _i, _la in enumerate(_la_rows):
        if _i == 0:
            continue
        _pid = int(_la.period_id) if _la.period_id is not None else None
        _prev_pid = (
            int(_la_rows[_i - 1].period_id) if _la_rows[_i - 1].period_id is not None else None
        )
        if _pid is not None and _prev_pid is not None and _pid != _prev_pid:
            _rla_margin_top_rows.append(_i + 1)

    _rla_period_labels = {1: "1er período", 2: "2do período", 3: "3er período"}
    for _ri, _la in enumerate(_la_rows, start=1):
        _nm = _qse_student_names_line([_la.student_id])
        _pid = int(_la.period_id) if _la.period_id is not None else None
        _plab = _rla_period_labels.get(_pid, f"Período {_pid}" if _pid is not None else "")
        replacements[f"rlane_1_{_ri}"] = " - ".join(x for x in (_nm, _plab) if x)
        replacements[f"rllr_1_{_ri}"] = (_la.achievements or "").strip()
        replacements[f"rlcs_1_{_ri}"] = (_la.comments or "").strip()
    _n_rla_rows = max(1, len(_la_rows))

    # IV/V — Tres tablas → tres bloques del DOCX (mapeo columnas BD → controles Word):
    #   course_activity_family    — Sección 1 IV familia:    rafcf_{i}_1 | rafcne/rafcnia/rafcnit | rafcniob=objectives … rafcnir=results
    #   course_activity_community — Sección 2 IV comunidad:  tceef_{i}_1 | tceen/tceeap/tceete | tceeo … tceer=results
    #   course_activity_other     — Sección 3 V acta:        arf_{i}_1 | arn/arpa/arr/art | arm / ara / arc
    #   i = bloque 1..N por tabla; orden por fila: date desc, id desc dentro de cada consulta.
    _RAFC_MAX_BLOCKS = 20
    _RAFC_MAX_PARTICIPANT_ROWS = 30
    _rafc_text_keys = ("rafcniob", "rafcniac", "rafcniacc", "rafcnir")
    for _bb in range(1, _RAFC_MAX_BLOCKS + 1):
        replacements[f"rafcf_{_bb}_1"] = ""
        for _k in _rafc_text_keys:
            replacements[f"{_k}_{_bb}_1"] = ""
        for _rr in range(1, _RAFC_MAX_PARTICIPANT_ROWS + 1):
            replacements[f"rafcne_{_bb}_{_rr}"] = ""
            replacements[f"rafcnia_{_bb}_{_rr}"] = ""
            replacements[f"rafcnit_{_bb}_{_rr}"] = ""
    _TCEE_MAX_BLOCKS = 20
    _tcee_text_keys = ("tceeo", "tceea", "tceeac", "tceer")
    for _bb in range(1, _TCEE_MAX_BLOCKS + 1):
        replacements[f"tceef_{_bb}_1"] = ""
        for _k in _tcee_text_keys:
            replacements[f"{_k}_{_bb}_1"] = ""
        for _rr in range(1, _RAFC_MAX_PARTICIPANT_ROWS + 1):
            replacements[f"tceen_{_bb}_{_rr}"] = ""
            replacements[f"tceeap_{_bb}_{_rr}"] = ""
            replacements[f"tceete_{_bb}_{_rr}"] = ""

    _AR_MAX_BLOCKS = 20
    for _bb in range(1, _AR_MAX_BLOCKS + 1):
        replacements[f"arf_{_bb}_1"] = ""
        for _k in ("arm", "ara", "arc"):
            replacements[f"{_k}_{_bb}_1"] = ""
        for _rr in range(1, _RAFC_MAX_PARTICIPANT_ROWS + 1):
            replacements[f"arn_{_bb}_{_rr}"] = ""
            replacements[f"arpa_{_bb}_{_rr}"] = ""
            replacements[f"arr_{_bb}_{_rr}"] = ""
            replacements[f"art_{_bb}_{_rr}"] = ""

    _car_all, _rafc_rows, _tcee_rows, _ar_rows = _split_course_activity_records_for_register_book(
        db, course_id
    )
    if len(_rafc_rows) > _RAFC_MAX_BLOCKS:
        logger.warning(
            "register_book: se omiten registros de actividades familia más allá de %s",
            _RAFC_MAX_BLOCKS,
        )
        _rafc_rows = _rafc_rows[:_RAFC_MAX_BLOCKS]
    if len(_tcee_rows) > _TCEE_MAX_BLOCKS:
        logger.warning(
            "register_book: se omiten registros de actividades comunidad más allá de %s",
            _TCEE_MAX_BLOCKS,
        )
        _tcee_rows = _tcee_rows[:_TCEE_MAX_BLOCKS]
    if len(_ar_rows) > _AR_MAX_BLOCKS:
        logger.warning(
            "register_book: se omiten registros de actas (other) más allá de %s",
            _AR_MAX_BLOCKS,
        )
        _ar_rows = _ar_rows[:_AR_MAX_BLOCKS]

    # Debug CAR: uvicorn en Windows suele NO mostrar print(); se escribe archivo + log WARNING.
    _car_dbg_path = Path("files/system/students") / "register_book_car_debug.txt"
    try:
        _car_dbg_path.parent.mkdir(parents=True, exist_ok=True)
        _lines = [
            "=== register_book: IV/V actividades (3 tablas) ===",
            f"course_id={course_id}",
            "",
            "TABLAS → PLANTILLA WORD:",
            "  course_activity_family    → IV familia   (rafcf_*, rafcne_*, rafcniob/ac/acc/nir)",
            "  course_activity_community → IV comunidad (tceef_*, tceen_*, tceeo/a/ac/er)",
            "  course_activity_other     → V acta       (arf_*, arn_*, arm/ara/arc)",
            "",
            f"Total filas (suma 3 tablas): {len(_car_all)}",
            f"Ids por tabla: family={[r.id for r in _rafc_rows]} "
            f"community={[r.id for r in _tcee_rows]} other={[r.id for r in _ar_rows]}",
            "",
            "--- Cada fila ---",
        ]
        for _sec, _rec in _car_all:
            _lines.append(
                f"id={_rec.id} section={_sec!r} date={getattr(_rec, 'date', None)}"
            )
            _lines.append(f"  objectives={getattr(_rec, 'objectives', None)!r}")
            _lines.append(f"  activities={getattr(_rec, 'activities', None)!r}")
            _lines.append(f"  agreements={getattr(_rec, 'agreements', None)!r}")
            _lines.append(f"  results={getattr(_rec, 'results', None)!r}")
            _lines.append(f"  attendees={getattr(_rec, 'attendees', None)!r}")
            _lines.append("")
        _lines.append("--- Cómo quedan los bloques (i=1..N por tipo) ---")
        _lines.append(
            "family:    registro índice i → rafcf_i_1, rafcne_i_fila… (objetivos=objectives, …)"
        )
        _lines.append(
            "community: registro índice i → tceef_i_1, tceen_i_fila… (objetivos=objectives, …)"
        )
        _lines.append(
            "other:     registro índice i → arf_i_1, arn_i_fila… (arm=motivo=objectives, ara=agreements, arc=results)"
        )
        _txt = "\n".join(_lines) + "\n"
        _car_dbg_path.write_text(_txt, encoding="utf-8")
        logger.warning(
            "register_book CAR: debug escrito en %s (stdout no siempre visible con uvicorn)",
            _car_dbg_path.resolve(),
        )
    except OSError as _e:
        logger.warning("register_book CAR: no se pudo escribir debug: %s", _e)

    def _rafc_fmt_date(_d) -> str:
        if _d is None:
            return ""
        if hasattr(_d, "strftime"):
            return _d.strftime("%d/%m/%Y")
        return str(_d)

    def _rafc_field_text(v) -> str:
        if v is None:
            return ""
        if isinstance(v, (bytes, bytearray)):
            return v.decode("utf-8", errors="replace").replace("\u00a0", " ").strip()
        return str(v).replace("\u00a0", " ").strip()

    for _bi, _rec in enumerate(_rafc_rows, start=1):
        replacements[f"rafcf_{_bi}_1"] = _rafc_fmt_date(_rec.date)
        _att = _load_attendees(_rec.attendees)
        if len(_att) > _RAFC_MAX_PARTICIPANT_ROWS:
            logger.warning(
                "register_book: se omiten participantes más allá de %s en actividad id=%s",
                _RAFC_MAX_PARTICIPANT_ROWS,
                getattr(_rec, "id", None),
            )
            _att = _att[:_RAFC_MAX_PARTICIPANT_ROWS]
        _rows = _att if _att else [None]
        for _rj, _one in enumerate(_rows, start=1):
            if _one is None:
                replacements[f"rafcne_{_bi}_{_rj}"] = ""
                replacements[f"rafcnia_{_bi}_{_rj}"] = ""
                replacements[f"rafcnit_{_bi}_{_rj}"] = ""
            else:
                replacements[f"rafcne_{_bi}_{_rj}"] = str(_one.get("name") or "").strip()
                replacements[f"rafcnia_{_bi}_{_rj}"] = attendees_rafcnia_line([_one])
                replacements[f"rafcnit_{_bi}_{_rj}"] = attendees_rafcnit_line([_one])
        replacements[f"rafcniob_{_bi}_1"] = _rafc_field_text(getattr(_rec, "objectives", None))
        replacements[f"rafcniac_{_bi}_1"] = _rafc_field_text(getattr(_rec, "activities", None))
        replacements[f"rafcniacc_{_bi}_1"] = _rafc_field_text(getattr(_rec, "agreements", None))
        replacements[f"rafcnir_{_bi}_1"] = _rafc_field_text(getattr(_rec, "results", None))
    _n_rafc_blocks = max(1, len(_rafc_rows))

    for _bi, _rec in enumerate(_tcee_rows, start=1):
        replacements[f"tceef_{_bi}_1"] = _rafc_fmt_date(_rec.date)
        _att = _load_attendees(_rec.attendees)
        if len(_att) > _RAFC_MAX_PARTICIPANT_ROWS:
            logger.warning(
                "register_book: se omiten participantes más allá de %s en actividad comunidad id=%s",
                _RAFC_MAX_PARTICIPANT_ROWS,
                getattr(_rec, "id", None),
            )
            _att = _att[:_RAFC_MAX_PARTICIPANT_ROWS]
        _rows = _att if _att else [None]
        for _rj, _one in enumerate(_rows, start=1):
            if _one is None:
                replacements[f"tceen_{_bi}_{_rj}"] = ""
                replacements[f"tceeap_{_bi}_{_rj}"] = ""
                replacements[f"tceete_{_bi}_{_rj}"] = ""
            else:
                replacements[f"tceen_{_bi}_{_rj}"] = str(_one.get("name") or "").strip()
                replacements[f"tceeap_{_bi}_{_rj}"] = attendees_rafcnia_line([_one])
                replacements[f"tceete_{_bi}_{_rj}"] = attendees_rafcnit_line([_one])
        replacements[f"tceeo_{_bi}_1"] = _rafc_field_text(getattr(_rec, "objectives", None))
        replacements[f"tceea_{_bi}_1"] = _rafc_field_text(getattr(_rec, "activities", None))
        replacements[f"tceeac_{_bi}_1"] = _rafc_field_text(getattr(_rec, "agreements", None))
        replacements[f"tceer_{_bi}_1"] = _rafc_field_text(getattr(_rec, "results", None))
    _n_tcee_blocks = max(1, len(_tcee_rows))

    for _bi, _rec in enumerate(_ar_rows, start=1):
        replacements[f"arf_{_bi}_1"] = _rafc_fmt_date(_rec.date)
        _att = _load_attendees(_rec.attendees)
        if len(_att) > _RAFC_MAX_PARTICIPANT_ROWS:
            logger.warning(
                "register_book: se omiten participantes más allá de %s en acta (other) id=%s",
                _RAFC_MAX_PARTICIPANT_ROWS,
                getattr(_rec, "id", None),
            )
            _att = _att[:_RAFC_MAX_PARTICIPANT_ROWS]
        _rows = _att if _att else [None]
        for _rj, _one in enumerate(_rows, start=1):
            if _one is None:
                replacements[f"arn_{_bi}_{_rj}"] = ""
                replacements[f"arpa_{_bi}_{_rj}"] = ""
                replacements[f"arr_{_bi}_{_rj}"] = ""
                replacements[f"art_{_bi}_{_rj}"] = ""
            else:
                replacements[f"arn_{_bi}_{_rj}"] = str(_one.get("name") or "").strip()
                replacements[f"arpa_{_bi}_{_rj}"] = attendees_rafcnia_line([_one])
                replacements[f"arr_{_bi}_{_rj}"] = attendee_rut_cell(_one)
                replacements[f"art_{_bi}_{_rj}"] = attendee_phone_cell(_one)
        replacements[f"arm_{_bi}_1"] = _rafc_field_text(getattr(_rec, "objectives", None))
        replacements[f"ara_{_bi}_1"] = _rafc_field_text(getattr(_rec, "agreements", None))
        replacements[f"arc_{_bi}_1"] = _rafc_field_text(getattr(_rec, "results", None))
    _n_ar_blocks = max(1, len(_ar_rows))

    # b) Adecuaciones curriculares — euaac_1..4, eaaam_1..4, peu_1..4, euae_1..4 (4 tipos por sort_order)
    for _k in range(1, 5):
        replacements[f"euaac_{_k}"] = ""
        replacements[f"eaaam_{_k}"] = ""
        replacements[f"peu_{_k}"] = ""
        replacements[f"euae_{_k}"] = ""
    _ca_types = (
        db.query(CurricularAdequacyTypeModel)
        .filter(CurricularAdequacyTypeModel.deleted_date.is_(None))
        .order_by(CurricularAdequacyTypeModel.sort_order)
        .limit(4)
        .all()
    )
    _ca_rows = (
        db.query(CourseCurricularAdequacyModel)
        .filter(
            CourseCurricularAdequacyModel.course_id == course_id,
            CourseCurricularAdequacyModel.deleted_date.is_(None),
        )
        .all()
    )
    _ca_by_type = {a.curricular_adequacy_type_id: a for a in _ca_rows}

    def _ca_subject_labels(_adj_id: int | None) -> str:
        if not _adj_id:
            return ""
        _sids = [
            t[0]
            for t in db.query(CourseCurricularAdequacySubjectModel.subject_id)
            .filter(CourseCurricularAdequacySubjectModel.course_curricular_adequacy_id == _adj_id)
            .all()
        ]
        if not _sids:
            return ""
        _parts: list = []
        for _sub_id in _sids:
            _sj = db.query(SubjectModel).filter(SubjectModel.id == _sub_id).first()
            if _sj and (_sj.subject or "").strip():
                _parts.append((_sj.subject or "").strip())
        return ", ".join(_parts)

    for _ci, _t in enumerate(_ca_types):
        if _ci >= 4:
            break
        _n = _ci + 1
        _adj = _ca_by_type.get(_t.id)
        if _adj:
            replacements[f"euaac_{_n}"] = "1" if getattr(_adj, "applied", 0) else ""
            _scope = (getattr(_adj, "scope_text", None) or "").strip()
            replacements[f"eaaam_{_n}"] = _scope if _scope else _ca_subject_labels(_adj.id)
            replacements[f"peu_{_n}"] = (getattr(_adj, "strategies_text", None) or "").strip()
            _stu_ids = [
                t[0]
                for t in db.query(CourseCurricularAdequacyStudentModel.student_id)
                .filter(CourseCurricularAdequacyStudentModel.course_curricular_adequacy_id == _adj.id)
                .all()
            ]
            replacements[f"euae_{_n}"] = _qse_student_names_line(_stu_ids)

    # c) Estrategias y procedimientos de evaluación — epea_1..2 (por tipo), epea_3 = OBSERVACIONES
    replacements["epea_1"] = ""
    replacements["epea_2"] = ""
    replacements["epea_3"] = ""
    _eval_div_types = (
        db.query(EvalDiversityTypeModel)
        .filter(EvalDiversityTypeModel.deleted_date.is_(None))
        .order_by(EvalDiversityTypeModel.sort_order)
        .limit(2)
        .all()
    )
    _eval_div_rows = (
        db.query(CourseEvalDiversityModel)
        .filter(
            CourseEvalDiversityModel.course_id == course_id,
            CourseEvalDiversityModel.deleted_date.is_(None),
        )
        .all()
    )
    _eval_by_type = {e.eval_diversity_type_id: e for e in _eval_div_rows}
    for _ei, _evt in enumerate(_eval_div_types):
        if _ei >= 2:
            break
        _evr = _eval_by_type.get(_evt.id)
        replacements[f"epea_{_ei + 1}"] = (
            (getattr(_evr, "strategies_text", None) or "").strip() if _evr else ""
        )
    _eval_div_obs = (
        db.query(CourseEvalDiversityObservationModel)
        .filter(
            CourseEvalDiversityObservationModel.course_id == course_id,
            CourseEvalDiversityObservationModel.deleted_date.is_(None),
        )
        .first()
    )
    if _eval_div_obs and (_eval_div_obs.observations or "").strip():
        replacements["epea_3"] = (_eval_div_obs.observations or "").strip()

    # 4. Plan de Apoyo Individual — un cuadro por alumno (no mezclar nombres). Hasta 5 filas por tabla;
    #    si un alumno tiene más de 5 apoyos, se usan tablas extra solo para ese alumno.
    _pai_rows = (
        db.query(CourseIndividualSupportModel)
        .filter(
            CourseIndividualSupportModel.course_id == course_id,
            CourseIndividualSupportModel.deleted_date.is_(None),
        )
        .order_by(CourseIndividualSupportModel.id)
        .all()
    )

    def _pai_fmt_date(_d) -> str:
        if _d is None:
            return ""
        if hasattr(_d, "strftime"):
            return _d.strftime("%d/%m/%Y")
        return str(_d)

    def _pai_student_sort_key(_sid: int) -> tuple:
        _p = (
            db.query(StudentPersonalInfoModel)
            .filter(StudentPersonalInfoModel.student_id == _sid)
            .first()
        )
        if not _p:
            return ("", _sid)
        _nm = f"{_p.names or ''} {_p.father_lastname or ''} {_p.mother_lastname or ''}".strip().lower()
        return (_nm, _sid)

    _sid_to_rows: dict[int, list] = defaultdict(list)
    for _psr in _pai_rows:
        for (_sid,) in (
            db.query(CourseIndividualSupportStudentModel.student_id)
            .filter(CourseIndividualSupportStudentModel.course_individual_support_id == _psr.id)
            .all()
        ):
            if not _sid:
                continue
            _lst = _sid_to_rows[_sid]
            if not any(_r.id == _psr.id for _r in _lst):
                _lst.append(_psr)
    for _sid in _sid_to_rows:
        _sid_to_rows[_sid].sort(key=lambda r: r.id)

    _pai_blocks: list[tuple[int, list]] = []
    for _sid in sorted(_sid_to_rows.keys(), key=_pai_student_sort_key):
        _rows = _sid_to_rows[_sid]
        for _chunk_start in range(0, len(_rows), 5):
            _pai_blocks.append((_sid, _rows[_chunk_start : _chunk_start + 5]))

    _n_pai_blocks = max(1, len(_pai_blocks))
    _max_paih = max(5, 5 * _n_pai_blocks)
    for _pp in range(1, _n_pai_blocks + 1):
        replacements[f"paie_{_pp}"] = ""
        replacements[f"aer_{_pp}"] = ""
        replacements[f"paio_{_pp}"] = ""
    for _pp in range(1, _max_paih + 1):
        replacements[f"paih_{_pp}"] = ""
        replacements[f"paifi_{_pp}"] = ""
        replacements[f"paift_{_pp}"] = ""

    for _bi, (_one_sid, _slice) in enumerate(_pai_blocks):
        for _j, _psr in enumerate(_slice):
            _pn = _bi * 5 + _j + 1
            replacements[f"paih_{_pn}"] = (_psr.horario or "").strip()
            replacements[f"paifi_{_pn}"] = _pai_fmt_date(_psr.fecha_inicio)
            replacements[f"paift_{_pn}"] = _pai_fmt_date(_psr.fecha_termino)
        replacements[f"paie_{_bi + 1}"] = _qse_student_names_line([_one_sid])
        if len(_slice) >= 5:
            replacements[f"aer_{_bi + 1}"] = (_slice[4].observations or "").strip()
        _obs_pie = [(_r.observations or "").strip() for _r in _slice[:4] if (_r.observations or "").strip()]
        replacements[f"paio_{_bi + 1}"] = "; ".join(_obs_pie)

    # 5. Familia y comunidad — etfd_1..4 (Descripción), etfs_1..4 (Seguimiento), etfe_1..4 (Evaluación)
    for _fc in range(1, 5):
        replacements[f"etfd_{_fc}"] = ""
        replacements[f"etfs_{_fc}"] = ""
        replacements[f"etfe_{_fc}"] = ""
    _fc_types = (
        db.query(FamilyCommunityStrategyTypeModel)
        .filter(FamilyCommunityStrategyTypeModel.deleted_date.is_(None))
        .order_by(FamilyCommunityStrategyTypeModel.sort_order)
        .limit(4)
        .all()
    )
    _fc_rows = (
        db.query(CourseFamilyCommunityModel)
        .filter(
            CourseFamilyCommunityModel.course_id == course_id,
            CourseFamilyCommunityModel.deleted_date.is_(None),
        )
        .all()
    )
    _fc_by_type = {r.family_community_strategy_type_id: r for r in _fc_rows}
    for _fi, _fty in enumerate(_fc_types):
        if _fi >= 4:
            break
        _frow = _fc_by_type.get(_fty.id)
        _fn = _fi + 1
        if _frow:
            replacements[f"etfd_{_fn}"] = (_frow.descripcion or "").strip()
            replacements[f"etfs_{_fn}"] = (_frow.seguimiento or "").strip()
            replacements[f"etfe_{_fn}"] = (_frow.evaluacion or "").strip()
    # Plantilla register_book.docx: control «OBSERVACIONES» = tag etfo (sin sufijo _1)
    replacements["etfo"] = ""
    replacements["etfo_1"] = ""
    _fc_obs = (
        db.query(CourseFamilyCommunityObservationModel)
        .filter(
            CourseFamilyCommunityObservationModel.course_id == course_id,
            CourseFamilyCommunityObservationModel.deleted_date.is_(None),
        )
        .first()
    )
    if _fc_obs and (_fc_obs.observations or "").strip():
        _etfo_txt = (_fc_obs.observations or "").strip()
        replacements["etfo"] = _etfo_txt
        replacements["etfo_1"] = _etfo_txt

    # Estrategias diversificadas (registro b): hasta 8 filas en orden de slot; asignatura vía ptc_regular si aplica
    for i in range(1, 9):
        replacements[f"regular_diversified_subject_{i}"] = ""
        replacements[f"regular_diversified_strategy_{i}"] = ""
        replacements[f"regular_diversified_period_{i}"] = ""
        replacements[f"regular_diversified_criteria_{i}"] = ""
        # Alias simples usados en algunos templates
        replacements[f"strategy_{i}"] = ""
        replacements[f"aada_{i}"] = ""
        replacements[f"pta_{i}"] = ""
        replacements[f"cee_{i}"] = ""
    # II a) Acciones de aplicación / evaluación de estrategias (plantilla: aesdt_1..17, aesdter_1..17)
    for _ai in range(1, 18):
        replacements[f"aesdt_{_ai}"] = ""
        replacements[f"aesdter_{_ai}"] = ""
    # aesdt_* / aesdter_*: differentiated_strategies_implementations (CourseSettings III.1.a:
    # applied_strategies = estrategia, actions_taken = evaluación). La tabla no tiene course_id
    # en el modelo actual; misma lista global que el front al cargar la sección.
    impl_rows = (
        db.query(DifferentiatedStrategiesImplementationModel)
        .filter(DifferentiatedStrategiesImplementationModel.deleted_date.is_(None))
        .order_by(DifferentiatedStrategiesImplementationModel.id)
        .all()
    )

    def _impl_period_bucket(row: DifferentiatedStrategiesImplementationModel) -> int:
        pid = row.period_id
        if pid in (1, 2, 3):
            return int(pid)
        return 1

    # Plantilla: 1er período → aesdt_1..6; 2do → aesdt_7..12; 3er → aesdt_13..17
    _PERIOD_SLOT_RANGE = {1: (1, 6), 2: (7, 12), 3: (13, 17)}
    _per_count = {1: 0, 2: 0, 3: 0}
    _by_slot: list[tuple[int, DifferentiatedStrategiesImplementationModel]] = []

    for impl in impl_rows:
        pid = _impl_period_bucket(impl)
        start, end = _PERIOD_SLOT_RANGE[pid]
        local = _per_count[pid]
        slot = start + local
        if slot > end:
            continue
        _per_count[pid] += 1
        _by_slot.append((slot, impl))

    _by_slot.sort(key=lambda t: t[0])

    for seq_idx, (i, impl) in enumerate(_by_slot):
        _strat = (impl.applied_strategies or "").strip()
        _crit = (impl.actions_taken or "").strip()
        _per = str(impl.period_id) if impl.period_id in (1, 2, 3) else ""

        subject_txt = ""
        if seq_idx < len(ptc_regular):
            _ptc, _prof = ptc_regular[seq_idx]
            subject_txt = (_ptc.subject or "").strip()
        elif _strat:
            subject_txt = _strat

        replacements[f"aesdt_{i}"] = _strat
        replacements[f"aesdter_{i}"] = _crit

        if seq_idx < 8:
            j = seq_idx + 1
            replacements[f"regular_diversified_subject_{j}"] = subject_txt
            replacements[f"regular_diversified_strategy_{j}"] = _strat
            replacements[f"regular_diversified_period_{j}"] = _per
            replacements[f"regular_diversified_criteria_{j}"] = _crit
            replacements[f"strategy_{j}"] = _strat
            replacements[f"aada_{j}"] = subject_txt
            replacements[f"pta_{j}"] = _per
            replacements[f"cee_{j}"] = _crit
    out_dir = Path("files/system/students")
    out_dir.mkdir(parents=True, exist_ok=True)
    course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
    course_name = (course.course_name or f"curso_{course_id}").replace(" ", "_")
    safe_name = re.sub(r"[^\w\-]", "", course_name)[:50]
    out_file = out_dir / f"libro_registro_{safe_name}_{uuid.uuid4().hex[:8]}.docx"
    # Clonar cuadros rarpo_* (un bloque por asignatura con datos en la UI)
    work_docx = out_dir / f"_rb_work_{uuid.uuid4().hex[:8]}.docx"
    result = {"status": "error", "message": "Error generando libro de registro"}
    try:
        shutil_copy(template_path, work_docx)
        _n_rarpo_blocks = min(len(_rb_subject_blocks), _RB_MAX_REGISTERS)
        clone_register_book_section_b_blocks(work_docx, _n_rarpo_blocks, _RB_ROWS_PER_REGISTER)
        clone_pai_support_tables(work_docx, _n_pai_blocks)
        clone_course_record_support_tables(work_docx, _n_raeg_blocks)
        for _ix, _blk in enumerate(_raeg_blocks, start=1):
            _nri = len(_blk["interventions"])
            if _nri > 1:
                expand_raeg_intervention_rows(
                    work_docx,
                    _ix,
                    min(_nri, _RAEG_MAX_ROWS),
                )
        expand_learning_achievement_rows(work_docx, 1, _n_rla_rows)
        apply_learning_achievement_period_top_spacing(work_docx, _rla_margin_top_rows)
        clone_course_activity_record_blocks(work_docx, _n_rafc_blocks)
        clone_course_community_activity_blocks(work_docx, _n_tcee_blocks)
        clone_course_acta_reunion_blocks(work_docx, _n_ar_blocks)
        for _ix, _rec in enumerate(_rafc_rows, start=1):
            _n_att = len(_load_attendees(_rec.attendees))
            _npr = max(1, min(_n_att, _RAFC_MAX_PARTICIPANT_ROWS) if _n_att else 1)
            if _npr > 1:
                expand_rafc_participant_rows(work_docx, _ix, _npr)
        for _ix, _rec in enumerate(_tcee_rows, start=1):
            _n_att = len(_load_attendees(_rec.attendees))
            _npr = max(1, min(_n_att, _RAFC_MAX_PARTICIPANT_ROWS) if _n_att else 1)
            if _npr > 1:
                expand_tcee_participant_rows(work_docx, _ix, _npr)
        for _ix, _rec in enumerate(_ar_rows, start=1):
            _n_att = len(_load_attendees(_rec.attendees))
            _npr = max(1, min(_n_att, _RAFC_MAX_PARTICIPANT_ROWS) if _n_att else 1)
            if _npr > 1:
                expand_arn_participant_rows(work_docx, _ix, _npr)
        result = DocumentsClass.fill_docx_form(str(work_docx), replacements, str(out_file))
    finally:
        try:
            work_docx.unlink(missing_ok=True)
        except OSError:
            pass
    if result.get("status") == "error":
        return None, result.get("message", "Error generando libro de registro")
    return str(out_file), None


@documents.get("/register_book/{course_id}")
async def get_register_book(
    course_id: int,
    db: Session = Depends(get_db),
    session_user: UserLogin = Depends(get_current_active_user),
):
    """
    Genera y descarga el documento 27 (Libro de registro) para un curso.
    URL: GET /api/documents/register_book/{course_id}
    """
    try:
        file_path, err = _generate_register_book_impl(course_id, db)
        if err:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND if "no encontrado" in err.lower() else status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 404 if "no encontrado" in err.lower() else 500, "message": err, "data": None},
            )
        return FileResponse(
            path=file_path,
            filename=Path(file_path).name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@documents.get("/generate/register_book/{course_id}")
async def generate_register_book(
    course_id: int,
    db: Session = Depends(get_db),
    session_user: UserLogin = Depends(get_current_active_user),
):
    """
    Genera el documento 27 (Libro de registro) en DOCX para un curso.
    Rellena regular_professional_* (teacher_type_id=1) y specialist_professional_* (teacher_type_id=2).
    """
    try:
        file_path, err = _generate_register_book_impl(course_id, db)
        if err:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND if "no encontrado" in err.lower() else status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 404 if "no encontrado" in err.lower() else 500, "message": err, "data": None},
            )
        return FileResponse(
            path=file_path,
            filename=Path(file_path).name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@documents.get("/register_book_car_preview/{course_id}")
async def register_book_car_preview(
    course_id: int,
    db: Session = Depends(get_db),
    session_user: UserLogin = Depends(get_current_active_user),
):
    """
    JSON: cómo se reparten los registros de actividad del curso en las 3 subsecciones del libro
    (family / community / other) y qué tags DOCX usa cada una. No genera DOCX.
    GET /api/documents/register_book_car_preview/{course_id}
    """
    _car_all, _rafc_rows, _tcee_rows, _ar_rows = _split_course_activity_records_for_register_book(
        db, course_id
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "course_id": course_id,
            "tables": {
                "family": "course_activity_family",
                "community": "course_activity_community",
                "other": "course_activity_other",
            },
            "mapping": {
                "1_family": "IV familia ← course_activity_family: rafcf_{i}_1, rafcne/rafcnia/rafcnit, rafcniob…rafcnir",
                "2_community": "IV comunidad ← course_activity_community: tceef_{i}_1, tceen/…, tceeo…tceer",
                "3_other": "V acta ← course_activity_other: arf_{i}_1, arn/…, arm/ara/arc",
            },
            "bucket_ids": {
                "family": [r.id for r in _rafc_rows],
                "community": [r.id for r in _tcee_rows],
                "other": [r.id for r in _ar_rows],
            },
            "rows_all": [_row_to_dict(r, _sec) for _sec, r in _car_all],
            "debug_file_after_generate": "files/system/students/register_book_car_debug.txt",
        },
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
        
        # Mensajes unificados para generación de documentos
        MSG_NO_DOC = "No se encontró documento para este estudiante."
        MSG_ERROR_GEN = "Error generando documento."
        
        # Obtener el documento usando la clase
        document = DocumentsClass(db)
        document_result = document.get(document_id)
        # Documentos 3,4,7,8,18,19,22,23,24,25,27 se pueden generar aunque no existan en la tabla documents
        known_generable = (3, 4, 7, 8, 9, 18, 19, 20, 22, 23, 24, 25, 27, 29, 31)
        if isinstance(document_result, dict) and document_result.get("status") == "error":
            if document_id in known_generable or _catalog_row_is_informe_evaluacion_psicomotriz(document_id, db):
                document_result = {"document_type_id": document_id}
            else:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": document_result.get("message", "Documento no encontrado"),
                        "data": None
                    }
                )
        
        # Si document_id = 3, generar documento de anamnesis (DOCX)
        if document_id == 3:
            result = _generate_anamnesis_docx_internal(student_id, db)
            if result.get("status") == "error":
                code = result.get("status_code", 500)
                return JSONResponse(
                    status_code=code,
                    content={
                        "status": code,
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None
                    }
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
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
                        "message": MSG_NO_DOC,
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
                        "message": MSG_NO_DOC,
                        "data": None
                    }
                )
            
            # Ruta del template - usar health_evaluation.docx
            template_path = Path("files/original_student_files") / "health_evaluation.docx"
            
            if not template_path.exists():
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": "Template de evaluación de salud no encontrado. Buscando: health_evaluation.docx",
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
            
            # Formatear fechas para DOCX
            def _fmt_date(val):
                if not val:
                    return ""
                try:
                    if isinstance(val, str):
                        dt = datetime.strptime(val.strip()[:10], "%Y-%m-%d").date()
                    else:
                        dt = val.date() if hasattr(val, "date") else val
                    return dt.strftime("%d/%m/%Y")
                except Exception:
                    return str(val) if val else ""
            
            # Edad en años y meses desde born_date
            age_str = ""
            bd_val = evaluation_data.get("born_date")
            ref_val = evaluation_data.get("evaluation_date") or None
            if bd_val:
                try:
                    if isinstance(bd_val, str):
                        born = datetime.strptime(bd_val.strip()[:10], "%Y-%m-%d").date()
                    else:
                        born = bd_val.date() if hasattr(bd_val, "date") else bd_val
                    ref = datetime.strptime(str(ref_val).strip()[:10], "%Y-%m-%d").date() if ref_val else date.today()
                    if born <= ref:
                        total_months = (ref.year - born.year) * 12 + (ref.month - born.month)
                        if ref.day < born.day:
                            total_months -= 1
                        years = total_months // 12
                        months = total_months % 12
                        age_str = f"{years} años {months} meses" if months else f"{years} años"
                except Exception:
                    pass
            if not age_str and evaluation_data.get("age") is not None:
                age_str = str(evaluation_data["age"])
            
            # Género (F/M para checkboxes)
            gender_marker = ""
            gn = evaluation_data.get("gender_name", "")
            if gn:
                gu = str(gn).upper()
                if "FEMENINO" in gu or gu == "F":
                    gender_marker = "F"
                elif "MASCULINO" in gu or gu == "M":
                    gender_marker = "M"
            
            # Procedencia: 1=Salud pública, 2=Particular, 3=Escuela, 4=Otro
            proc_id = evaluation_data.get("procedence_id")
            sp_val = "1" if proc_id == 1 else "0"
            p_val = "1" if proc_id == 2 else "0"
            e_val = "1" if proc_id == 3 else "0"
            o_val = "1" if proc_id == 4 else "0"
            proc_labels = {1: "Salud pública", 2: "Particular", 3: "Escuela", 4: "Otro"}
            professional_procedence_val = proc_labels.get(proc_id, "") if proc_id else ""
            if proc_id == 4:
                professional_procedence_val = str(evaluation_data.get("procedence_other") or "").strip()
            
            # Motivo: 1=EGS, otro=DDD
            cr_id = evaluation_data.get("consultation_reason_id")
            egs_val = "1" if cr_id == 1 else "0"
            ddd_val = "1" if (cr_id and cr_id != 1) else "0"
            
            # Construir replacements para DOCX
            full_name_val = str(evaluation_data.get("full_name") or "").strip()
            identification_val = str(evaluation_data.get("identification_number") or "").strip()
            born_date_val = _fmt_date(evaluation_data.get("born_date"))
            native_lang_val = str(evaluation_data.get("native_language") or "").strip()
            lang_used_val = str(evaluation_data.get("language_usually_used") or "").strip()
            nationality_val = str(evaluation_data.get("nationality_name") or "").strip()
            replacements = {
                "full_name": full_name_val,
                "names_lastnames": full_name_val,
                "identification_number": identification_val,
                "identificator_number": identification_val,
                "born_date": born_date_val,
                "birth_date": born_date_val,
                "age": age_str,
                "native_language": native_lang_val,
                "mother_language": native_lang_val,
                "language_usually_used": lang_used_val,
                "used_language": lang_used_val,
                "nationality_name": nationality_val,
                "nationality": nationality_val,
                "consultation_reason_detail": str(evaluation_data.get("consultation_reason_detail") or "").strip(),
                "professional_identification_number": str(evaluation_data.get("professional_identification_number") or "").strip(),
                "professional_registration_number": str(evaluation_data.get("professional_registration_number") or "").strip(),
                "professional_fullname": str(evaluation_data.get("professional_fullname") or "").strip(),
                "professional_full_name": str(evaluation_data.get("professional_fullname") or "").strip(),
                "professional_number": str(evaluation_data.get("professional_registration_number") or "").strip(),
                "professional_specialty_name": str(evaluation_data.get("professional_specialty_name") or "").strip(),
                "professional_speciality": str(evaluation_data.get("professional_specialty_name") or "").strip(),
                "procedence_other": str(evaluation_data.get("procedence_other") or "").strip(),
                "another_procedence": str(evaluation_data.get("procedence_other") or "").strip(),
                "professional_procedence": professional_procedence_val,
                "professional_contact": str(evaluation_data.get("professional_contact") or "").strip(),
                "phone_email": str(evaluation_data.get("professional_contact") or "").strip(),
                "evaluation_date": _fmt_date(evaluation_data.get("evaluation_date")),
                "reevaluation_date": _fmt_date(evaluation_data.get("reevaluation_date")),
                "general_assessment": str(evaluation_data.get("general_assessment") or "").strip(),
                "general_health_state": str(evaluation_data.get("general_assessment") or "").strip(),
                "diagnosis": str(evaluation_data.get("diagnosis") or "").strip(),
                "diagnostic": str(evaluation_data.get("diagnosis") or "").strip(),
                "indications": str(evaluation_data.get("indications") or "").strip(),
                "gender_name": str(evaluation_data.get("gender_name") or "").strip(),
                "gender_F": "1" if gender_marker == "F" else "0",
                "gender_M": "1" if gender_marker == "M" else "0",
                "sex_f": "1" if gender_marker == "F" else "0",
                "sex_m": "1" if gender_marker == "M" else "0",
                "procedence_SP": sp_val,
                "procedence_P": p_val,
                "procedence_E": e_val,
                "procedence_O": o_val,
                "procedence_1": sp_val,
                "procedence_2": p_val,
                "procedence_3": e_val,
                "procedence_4": o_val,
                "EGS": egs_val,
                "DDD": ddd_val,
                "consultation_reason_1": egs_val,
                "consultation_reason_2": ddd_val,
                "consultation_reason": str(evaluation_data.get("consultation_reason_detail") or "").strip(),
                "RUN": str(evaluation_data.get("identification_number") or "").strip(),
                "BD": _fmt_date(evaluation_data.get("born_date")),
                "DD": str(evaluation_data.get("consultation_reason_detail") or "").strip(),
                "Rut": str(evaluation_data.get("professional_identification_number") or "").strip(),
                "PRN": str(evaluation_data.get("professional_registration_number") or "").strip(),
                "OL": str(evaluation_data.get("native_language") or "").strip(),
                "HL": str(evaluation_data.get("language_usually_used") or "").strip(),
            }
            
            # Generar DOCX
            out_dir = Path("files/system/students")
            out_dir.mkdir(parents=True, exist_ok=True)
            safe_name = re.sub(r'[^\w\s-]', '', (evaluation_data.get("full_name") or "evaluacion")).replace(" ", "_")[:30]
            out_file = out_dir / f"evaluacion_salud_{safe_name}_{uuid.uuid4().hex[:8]}.docx"
            result = DocumentsClass.fill_docx_form(
                str(template_path),
                replacements,
                str(out_file),
            )
            
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None
                    }
                )
            
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        # Si document_id = 7, generar informe familiar (family_report)
        if document_id == 7:
            family_report_service = FamilyReportClass(db)
            fr_data = family_report_service.get_by_student_id(student_id)

            if isinstance(fr_data, dict) and fr_data.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None
                    }
                )

            template_path = Path("files/original_student_files") / "family_report.docx"
            if not template_path.exists():
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": "Template family_report.docx no encontrado",
                        "data": None
                    }
                )

            def _fmt_date(val):
                if not val:
                    return ""
                try:
                    if isinstance(val, str):
                        dt = datetime.strptime(val.strip()[:10], "%Y-%m-%d").date()
                    else:
                        dt = val.date() if hasattr(val, "date") else val
                    return dt.strftime("%d/%m/%Y")
                except Exception:
                    return str(val) if val else ""

            student_full_name = str(fr_data.get("student_full_name") or "").strip()
            student_identification = str(fr_data.get("student_identification_number") or "").strip()
            student_born = _fmt_date(fr_data.get("student_born_date"))
            student_age = str(fr_data.get("student_age") or "").strip()
            student_course = str(fr_data.get("student_course") or "").strip()
            student_school = str(fr_data.get("student_school") or "").strip()
            professional_full = str(fr_data.get("professional_social_name") or "").strip()
            professional_id_num = str(fr_data.get("professional_identification_number") or "").strip()
            professional_role = str(fr_data.get("professional_role") or "").strip()
            ph = str(fr_data.get("professional_phone") or "").strip()
            em = str(fr_data.get("professional_email") or "").strip()
            professional_phone_email = f"{ph} / {em}".strip(" / ") if (ph or em) else ""
            report_delivery = _fmt_date(fr_data.get("report_delivery_date"))
            receiver_full = str(fr_data.get("receiver_full_name") or "").strip()
            receiver_id_num = str(fr_data.get("receiver_identification_number") or "").strip()
            receiver_relation = str(fr_data.get("receiver_relationship") or "").strip()
            receiver_presence = str(fr_data.get("receiver_presence_of") or "").strip()
            evaluation_reason = str(fr_data.get("evaluation_reason") or fr_data.get("applied_instruments") or "").strip()
            diagnostic = str(fr_data.get("diagnosis") or "").strip()
            eval_type = (str(fr_data.get("evaluation_type") or "").strip()).lower()
            is_admission = eval_type in ("admission", "admisión", "ingreso", "1")
            is_reevaluation = eval_type in ("revaluation", "reevaluación", "2")
            strengths_1 = str(fr_data.get("pedagogical_strengths") or "").strip()
            support_needs_1 = str(fr_data.get("pedagogical_support_needs") or "").strip()
            strengths_2 = str(fr_data.get("social_affective_strengths") or "").strip()
            support_needs_2 = str(fr_data.get("social_affective_support_needs") or "").strip()
            strengths_3 = str(fr_data.get("health_strengths") or fr_data.get("strengths_3") or "").strip()
            support_needs_3 = str(fr_data.get("health_support_needs") or fr_data.get("support_needs_3") or "").strip()
            educational_supports_school = str(fr_data.get("collaborative_work") or "").strip()
            home_based_description = str(fr_data.get("home_based_description") or fr_data.get("home_support") or "").strip()
            collaborative_work = str(fr_data.get("collaborative_work") or "").strip()
            school_family_agreements = str(fr_data.get("school_family_agreements") or fr_data.get("agreements_commitments") or "").strip()
            eval_date_1 = _fmt_date(fr_data.get("evaluation_date_1"))
            eval_date_2 = _fmt_date(fr_data.get("evaluation_date_2"))
            eval_date_3 = _fmt_date(fr_data.get("evaluation_date_3"))

            replacements = {
                # Identificación del estudiante
                "student_full_name": student_full_name,
                "student_identification_number": student_identification,
                "student_birth_date": student_born,
                "student_born_date": student_born,
                "student_age": student_age,
                "student_course": student_course,
                "student_school": student_school,
                "RUN": student_identification,
                "Nombres y Apellidos": student_full_name,
                "Fecha nacimiento": student_born,
                "Edad": student_age,
                "Curso / Nivel": student_course,
                "Curso": student_course,
                "Establecimiento": student_school,
                # Identificación del profesional
                "professional_full_name": professional_full,
                "professional_social_name": professional_full,
                "professional_identification_number": professional_id_num,
                "professional_job_position": professional_role,
                "professional_role": professional_role,
                "professional_phone_email": professional_phone_email,
                "professional_phone": ph,
                "professional_email": em,
                "professional_delivered_date_inform": report_delivery,
                "report_delivery_date": report_delivery,
                "Nombre": professional_full,
                "Rut": professional_id_num,
                "Rol / cargo": professional_role,
                "Teléfono / E-mail de contacto": professional_phone_email,
                "Teléfono / E-mail": professional_phone_email,
                "Fecha entrega de informe": report_delivery,
                "Fecha entrega": report_delivery,
                # Identificación de la persona que recibe la información
                "person_full_name": receiver_full,
                "person_identification_number": receiver_id_num,
                "person_relation_student": receiver_relation,
                "person_presence_of": receiver_presence,
                "receiver_full_name": receiver_full,
                "receiver_identification_number": receiver_id_num,
                "receiver_relationship": receiver_relation,
                "receiver_presence_of": receiver_presence,
                # Resultados de la evaluación
                "evaluation_reason": evaluation_reason,
                "diagnostic": diagnostic,
                "diagnosis": diagnostic,
                "evaluation": "1" if is_admission else "",
                "reevaluation": "1" if is_reevaluation else "",
                # Fortalezas y necesidades de apoyo por ámbito
                "strengths_1": strengths_1,
                "support_needs_1": support_needs_1,
                "strengths_2": strengths_2,
                "support_needs_2": support_needs_2,
                "strengths_3": strengths_3,
                "support_needs_3": support_needs_3,
                "pedagogical_strengths": strengths_1,
                "pedagogical_support_needs": support_needs_1,
                "social_affective_strengths": strengths_2,
                "social_affective_support_needs": support_needs_2,
                "health_strengths": strengths_3,
                "health_support_needs": support_needs_3,
                # Alias para plantilla (ÁMBITO SOCIAL/AFECTIVO)
                "fortalezas_2": strengths_2,
                "necesidades_apoyo_2": support_needs_2,
                "ambito_social_fortalezas": strengths_2,
                "ambito_social_necesidades": support_needs_2,
                "fortalezas_social_afectivo": strengths_2,
                "necesidades_social_afectivo": support_needs_2,
                # Apoyos educativos escuela y hogar
                "educational_supports_school": educational_supports_school,
                "home_based_description": home_based_description,
                "collaborative_work": collaborative_work,
                "home_support": home_based_description,
                # Acuerdos y compromisos
                "school_family_agreements": school_family_agreements,
                "agreements_commitments": school_family_agreements,
                # Fechas en que se evaluarán los avances y logros
                "evaluation_date_1": eval_date_1,
                "evaluation_date_2": eval_date_2,
                "evaluation_date_3": eval_date_3,
            }

            out_dir = Path("files/system/students")
            out_dir.mkdir(parents=True, exist_ok=True)
            safe_name = re.sub(r'[^\w\s-]', '', (student_full_name or "informe_familiar")).replace(" ", "_")[:30]
            out_file = out_dir / f"informe_familiar_{safe_name}_{uuid.uuid4().hex[:8]}.docx"
            result = DocumentsClass.fill_docx_form(
                str(template_path),
                replacements,
                str(out_file),
            )

            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None
                    }
                )

            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        # Si document_id = 24, generar documento de interconsulta (interconsultation.docx)
        if document_id == 24:
            def _fmt_date_ic(val):
                if not val:
                    return ""
                try:
                    if isinstance(val, str):
                        dt = datetime.strptime(val.strip()[:10], "%Y-%m-%d").date()
                    else:
                        dt = val.date() if hasattr(val, "date") else val
                    return dt.strftime("%d/%m/%Y")
                except Exception:
                    return str(val) if val else ""

            interconsultation_service = InterconsultationClass(db)
            ic_data = interconsultation_service.get_by_student_id(student_id)
            student_full_name = ""
            student_identification_number = ""
            student_birth_date = ""
            student_age = ""
            student_mother_language = ""
            student_used_language = ""
            student_address = ""
            student_city = ""
            relation_with_student = ""
            establishment_address = ""
            establishment_commune = ""
            establishment_phone = ""
            establishment_email = ""
            student_phone = ""
            student_email = ""
            school = ""
            course = ""
            commune_id = None
            region_id = None
            responsible_id = None
            program_type_id = None
            additional_information_id = None
            attached_documents = None
            question = ""
            referring_professional = ""
            reception_date = ""
            evaluation_summary = ""
            indications_support = ""
            gender_id = None
            nationality_id = None
            professional_full_name = ""
            professional_identification_number = ""
            professional_registration_number = ""
            professional_specialty = ""
            professional_phone = ""
            procedence_id = None
            procedence_other = ""
            required_new_control_id = None
            required_new_control_date = ""
            evaluation_date = ""
            if isinstance(ic_data, dict) and ic_data.get("status") != "error":
                student_full_name = str(ic_data.get("full_name") or "").strip()
                student_identification_number = str(ic_data.get("identification_number") or "").strip()
                def _to_int(x):
                    if x is None or (isinstance(x, str) and x.strip() == ""):
                        return None
                    try:
                        return int(x)
                    except (TypeError, ValueError):
                        return None
                gender_id = _to_int(ic_data.get("gender_id"))
                nationality_id = _to_int(ic_data.get("nationality_id"))
                commune_id = _to_int(ic_data.get("commune_id"))
                region_id = _to_int(ic_data.get("region_id"))
                responsible_id = _to_int(ic_data.get("responsible_id"))
                student_birth_date = _fmt_date_ic(ic_data.get("born_date"))
                student_mother_language = str(ic_data.get("native_language") or "").strip()
                student_used_language = str(ic_data.get("language_usually_used") or "").strip()
                student_address = str(ic_data.get("address") or "").strip()
                student_city = str(ic_data.get("city") or "").strip()
                student_phone = str(ic_data.get("contact_phone") or "").strip()
                student_email = str(ic_data.get("contact_email") or "").strip()
                school = str(ic_data.get("educational_establishment") or "").strip()
                course = str(ic_data.get("course_level") or "").strip()
                program_type_id = _to_int(ic_data.get("program_type_id"))
                additional_information_id = _to_int(ic_data.get("additional_information_id"))
                attached_documents = ic_data.get("attached_documents")
                question = str(ic_data.get("question_to_answer") or "").strip()
                referring_professional = str(ic_data.get("referring_professional") or "").strip()
                reception_date = _fmt_date_ic(ic_data.get("reception_date"))
                evaluation_summary = str(ic_data.get("evaluation_summary") or "").strip()
                indications_support = str(ic_data.get("indications_support") or "").strip()
                establishment_address = str(ic_data.get("establishment_address") or "").strip()
                establishment_commune = str(ic_data.get("establishment_commune") or "").strip()
                establishment_phone = str(ic_data.get("establishment_phone") or "").strip()
                establishment_email = str(ic_data.get("establishment_email") or "").strip()
                professional_identification_number = str(ic_data.get("professional_identification_number") or "").strip()
                professional_registration_number = str(ic_data.get("professional_registration_number") or "").strip()
                professional_specialty = str(ic_data.get("professional_specialty") or "").strip()
                professional_phone = str(ic_data.get("professional_contact_phone") or "").strip()
                # professional_full_name y professional_specialty desde ProfessionalModel si hay professional_id
                _pid = _to_int(ic_data.get("professional_id"))
                if _pid:
                    _prof = db.query(ProfessionalModel).filter(ProfessionalModel.id == _pid).first()
                    if _prof:
                        professional_full_name = f"{_prof.names or ''} {_prof.lastnames or ''}".strip()
                        # Especialidad desde career_type_id del profesional si no viene en ic_data
                        if not professional_specialty and getattr(_prof, "career_type_id", None):
                            from app.backend.db.models import CareerTypeModel
                            _ct = db.query(CareerTypeModel).filter(CareerTypeModel.id == _prof.career_type_id).first()
                            if _ct and getattr(_ct, "career_type", None):
                                professional_specialty = str(_ct.career_type).strip()
                # Si professional_specialty viene como ID (número), resolver al nombre; si viene texto (ej. "Pediatra"), usarlo tal cual
                _raw_spec = ic_data.get("professional_specialty")
                if _raw_spec is not None:
                    _raw_str = str(_raw_spec).strip()
                    if _raw_str and (_raw_str.isdigit() or isinstance(_raw_spec, (int, float))):
                        try:
                            _sid = int(_raw_spec)
                            from app.backend.db.models import CareerTypeModel
                            _ct = db.query(CareerTypeModel).filter(CareerTypeModel.id == _sid).first()
                            if _ct and getattr(_ct, "career_type", None):
                                professional_specialty = str(_ct.career_type).strip()
                        except (TypeError, ValueError):
                            pass
                    elif not professional_specialty:
                        professional_specialty = _raw_str
                procedence_id = _to_int(ic_data.get("procedence_id"))
                procedence_other = str(ic_data.get("procedence_other") or "").strip()
                required_new_control_id = _to_int(ic_data.get("required_new_control_id"))
                required_new_control_date = _fmt_date_ic(ic_data.get("new_control_date"))
                evaluation_date = _fmt_date_ic(ic_data.get("evaluation_date"))
            student_data = student_result.get("student_data", {}) or {}
            personal = student_data.get("personal_data", {}) or {}
            academic = student_data.get("academic_info", {}) or {}
            if not student_full_name:
                student_full_name = f"{personal.get('names', '') or ''} {personal.get('father_lastname', '') or ''} {personal.get('mother_lastname', '') or ''}".strip() or f"Estudiante {student_id}"
            if not student_identification_number:
                student_identification_number = str(student_data.get("identification_number") or "").strip() or str(student_id)
            if not student_birth_date:
                student_birth_date = _fmt_date_ic(personal.get("born_date"))
            if not student_mother_language:
                student_mother_language = str(personal.get("native_language") or personal.get("mother_language") or "").strip()
            if not student_used_language:
                student_used_language = str(personal.get("language_usually_used") or personal.get("used_language") or "").strip()
            if not student_address:
                student_address = str(personal.get("address") or "").strip()
            if not student_city:
                student_city = str(personal.get("city") or "").strip()
            if not student_phone:
                student_phone = str(personal.get("phone") or "").strip()
            if not student_email:
                student_email = str(personal.get("email") or "").strip()
            if not school and student_data.get("school_id") and db:
                sch = db.query(SchoolModel).filter(SchoolModel.id == student_data["school_id"]).first()
                if sch:
                    school = str(sch.school_name or "").strip()
            if not course and academic.get("course_id") and db:
                crs = db.query(CourseModel).filter(CourseModel.id == academic["course_id"]).first()
                if crs:
                    course = str(crs.course_name or "").strip()
            guardian = None
            if db:
                guardian = db.query(StudentGuardianModel).filter(StudentGuardianModel.student_id == student_id).order_by(StudentGuardianModel.id.desc()).first()
            if responsible_id and db:
                fm = db.query(FamilyMemberModel).filter(FamilyMemberModel.id == responsible_id).first()
                if fm:
                    relation_with_student = str(fm.family_member or "").strip()
            if not relation_with_student and guardian and getattr(guardian, "family_member_id", None):
                fm = db.query(FamilyMemberModel).filter(FamilyMemberModel.id == guardian.family_member_id).first()
                if fm:
                    relation_with_student = str(fm.family_member or "").strip()
            if not establishment_address and student_data.get("school_id") and db:
                sch = db.query(SchoolModel).filter(SchoolModel.id == student_data["school_id"]).first()
                if sch:
                    establishment_address = str(getattr(sch, "school_address", None) or "").strip()
            # Edad siempre calculada desde fecha de nacimiento (años y meses)
            student_age = ""
            born_raw = ic_data.get("born_date") if isinstance(ic_data, dict) and ic_data.get("status") != "error" else None
            if born_raw is None:
                born_raw = personal.get("born_date")
            if born_raw:
                try:
                    dt = datetime.strptime(str(born_raw).strip()[:10], "%Y-%m-%d").date() if isinstance(born_raw, str) else (born_raw.date() if hasattr(born_raw, "date") else born_raw)
                    today = date.today()
                    years = today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))
                    total_months = (today.year - dt.year) * 12 + (today.month - dt.month)
                    if today.day < dt.day:
                        total_months -= 1
                    months = total_months % 12
                    parts = []
                    if years > 0:
                        parts.append(f"{years} año{'s' if years != 1 else ''}")
                    if months > 0:
                        parts.append(f"{months} mes{'es' if months != 1 else ''}")
                    student_age = " y ".join(parts) if parts else "0 años"
                except Exception:
                    pass
            def _int_or_none(v):
                if v is None or (isinstance(v, str) and v.strip() == ""):
                    return None
                try:
                    return int(v)
                except (TypeError, ValueError):
                    return None
            if gender_id is None:
                gender_id = _int_or_none(personal.get("gender_id"))
            if nationality_id is None:
                nationality_id = _int_or_none(personal.get("nationality_id"))
            if commune_id is None:
                commune_id = _int_or_none(personal.get("commune_id"))
            if region_id is None:
                region_id = _int_or_none(personal.get("region_id"))
            student_nationality = ""
            if nationality_id and db:
                nat = db.query(NationalityModel).filter(NationalityModel.id == nationality_id).first()
                if nat:
                    student_nationality = str(nat.nationality or "").strip()
            student_commune = ""
            if commune_id and db:
                comm = db.query(CommuneModel).filter(CommuneModel.id == commune_id).first()
                if comm:
                    student_commune = str(comm.commune or "").strip()
            student_region = ""
            if region_id and db:
                reg = db.query(RegionModel).filter(RegionModel.id == region_id).first()
                if reg:
                    student_region = str(reg.region or "").strip()
            # Checkboxes sexo: "1" = marcado, "" = desmarcado (igual que program_type_id_1/2/3, additional_information_1/2/3, document_1..10)
            sex_f = ""
            sex_m = ""
            if gender_id and db:
                g = db.query(GenderModel).filter(GenderModel.id == gender_id).first()
                gn = str(g.gender).lower().strip() if g and g.gender else ""
                if gn:
                    if "femenino" in gn or gn == "f" or "female" in gn or "mujer" in gn:
                        sex_f, sex_m = str("1"), str("")
                    elif "masculino" in gn or gn == "m" or "male" in gn or "hombre" in gn:
                        sex_f, sex_m = str(""), str("1")
            # program_type_id viene solo de la tabla interconsultations (1, 2 o 3): 1=Programa integración, 2=Escuela especial permanente, 3=Otro
            pt = _int_or_none(program_type_id)
            if pt is not None and pt not in (1, 2, 3):
                pt = None
            program_type_id_1 = str("1" if pt == 1 else "")
            program_type_id_2 = str("1" if pt == 2 else "")
            program_type_id_3 = str("1" if pt == 3 else "")
            # Procedencia: checkboxes procedence_id_1..3 (1=Salud pública, 2=Particular, 3=Otro); texto "Otro: especificar" solo si seleccionó Otro
            pproc = _int_or_none(procedence_id)
            if pproc is not None and pproc not in (1, 2, 3):
                pproc = None
            procedence_id_1 = str("1" if pproc == 1 else "")
            procedence_id_2 = str("1" if pproc == 2 else "")
            procedence_id_3 = str("1" if pproc == 3 else "")
            # Si selecciona Salud pública o Particular, el texto "Otro: especificar" queda en blanco; solo se rellena cuando selecciona Otro
            procedence_other_display = str(procedence_other) if pproc == 3 else ""
            # Requiere nuevo control: checkboxes required_new_control_id_1=SI, required_new_control_id_2=NO; texto required_new_control_date (Fecha)
            rnc = _int_or_none(required_new_control_id)
            if rnc is not None and rnc not in (1, 2):
                rnc = None
            required_new_control_id_1 = str("1" if rnc == 1 else "")
            required_new_control_id_2 = str("1" if rnc == 2 else "")
            # 1=Programa de integración, 2=Escuela especial permanente, 3=Otro — texto para sustituir en el documento
            if pt == 1:
                program_type_name = "Programa de integración"
            elif pt == 2:
                program_type_name = "Escuela especial permanente"
            elif pt == 3:
                program_type_name = "Otro"
            else:
                program_type_name = ""
            # Se requiere información adicional para: 1=descartar, 2=precisar, 3=complementar (solo additional_information_id)
            ai_set = set()
            ai_val = _int_or_none(additional_information_id)
            if ai_val is not None and 1 <= ai_val <= 3:
                ai_set.add(ai_val)
            # 1=descartar, 2=precisar, 3=complementar — mismo que sex_f/sex_m: "1" marcado, "" desmarcado
            additional_information_1 = str("1" if 1 in ai_set else "")
            additional_information_2 = str("1" if 2 in ai_set else "")
            additional_information_3 = str("1" if 3 in ai_set else "")
            # document_1..10 son checkboxes; valores "1" = marcado, "" = desmarcado. Vienen de attached_documents (tabla interconsultations).
            # La BD puede venir como números "1,2,5" o como texto "Anamnesis, Entrevista a la familia, Observación en la escuela, Informe Escolar, ..."
            # Mapeo: 1=Anamnesis, 2=Entrevista a la familia, 3=Observación en la escuela, 4=Examen de salud, 5=Informe escolar, 6=Informe social, 7=Informe neurológico, 8=Informe psicológico, 9=Informe fonoaudiológico, 10=Otro(s)
            def _attached_text_to_id(part: str) -> Optional[int]:
                p = (part or "").strip().lower()
                if not p:
                    return None
                if p.isdigit():
                    v = int(p)
                    return v if 1 <= v <= 10 else None
                if "anamnesis" in p:
                    return 1
                if "entrevista" in p and "familia" in p:
                    return 2
                if "observación" in p and "escuela" in p:
                    return 3
                if "examen" in p and "salud" in p:
                    return 4
                if "escolar" in p:
                    return 5
                if "social" in p:
                    return 6
                if "neurológico" in p:
                    return 7
                if "psicológico" in p:
                    return 8
                if "fonoaudiológico" in p:
                    return 9
                if "otro" in p:
                    return 10
                return None
            attached_set = set()
            if attached_documents is not None:
                if isinstance(attached_documents, str):
                    for part in attached_documents.split(","):
                        vid = _attached_text_to_id(part)
                        if vid is not None:
                            attached_set.add(vid)
                elif isinstance(attached_documents, (list, tuple)):
                    for x in attached_documents:
                        if isinstance(x, (int, float)) and 1 <= int(x) <= 10:
                            attached_set.add(int(x))
                        else:
                            vid = _attached_text_to_id(str(x))
                            if vid is not None:
                                attached_set.add(vid)
            document_1 = str("1" if 1 in attached_set else "")
            document_2 = str("1" if 2 in attached_set else "")
            document_3 = str("1" if 3 in attached_set else "")
            document_4 = str("1" if 4 in attached_set else "")
            document_5 = str("1" if 5 in attached_set else "")
            document_6 = str("1" if 6 in attached_set else "")
            document_7 = str("1" if 7 in attached_set else "")
            document_8 = str("1" if 8 in attached_set else "")
            document_9 = str("1" if 9 in attached_set else "")
            document_10 = str("1" if 10 in attached_set else "")
            template_path = Path("files/original_student_files") / "interconsultation.docx"
            if not template_path.exists():
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": "Template interconsultation.docx no encontrado en files/original_student_files",
                        "data": None
                    }
                )

            replacements = {
                "student_full_name": student_full_name,
                "student_identification_number": student_identification_number,
                "student_birth_date": student_birth_date,
                "student_age": student_age,
                "student_nationality": student_nationality,
                "student_mother_language": student_mother_language,
                "student_used_language": student_used_language,
                "student_address": student_address,
                "student_commune": student_commune,
                "student_region": student_region,
                "student_city": student_city,
                "relation_with_student": relation_with_student,
                "establishment_address": establishment_address,
                "establishment_commune": establishment_commune,
                "establishment_phone": establishment_phone,
                "establishment_email": establishment_email,
                "student_phone": student_phone,
                "student_email": student_email,
                "school": school,
                "course": course,
                "question": question,
                "referring_professional": referring_professional,
                "reception_date": reception_date,
                "evaluation_summary": evaluation_summary,
                "indications_support": indications_support,
                "p1": program_type_id_1,
                "p2": program_type_id_2,
                "p3": program_type_id_3,
                "program_type_name": program_type_name,
                "programa_integracion": "Programa de integración" if pt == 1 else "",
                "escuela_especial_permanente": "Escuela especial permanente" if pt == 2 else "",
                "program_type_otro": "Otro" if pt == 3 else "",
                "additional_information_1": additional_information_1,
                "additional_information_2": additional_information_2,
                "additional_information_3": additional_information_3,
                "descartar": additional_information_1,
                "precisar": additional_information_2,
                "complementar": additional_information_3,
                "document_1": document_1,
                "document_2": document_2,
                "document_3": document_3,
                "document_4": document_4,
                "document_5": document_5,
                "document_6": document_6,
                "document_7": document_7,
                "document_8": document_8,
                "document_9": document_9,
                "document_10": document_10,
                "sex_f": sex_f,
                "sex_m": sex_m,
                "professional_full_name": professional_full_name,
                "professional_identification_number": professional_identification_number,
                "professional_registration_number": professional_registration_number,
                "professional_specialty": professional_specialty,
                "professional_phone": professional_phone,
                "procedence_id_1": procedence_id_1,
                "procedence_id_2": procedence_id_2,
                "procedence_id_3": procedence_id_3,
                "procedence": procedence_other_display,
                "procedence_other": procedence_other_display,
                "procedence_otro": procedence_other_display,
                "required_new_control_id_1": required_new_control_id_1,
                "required_new_control_id_2": required_new_control_id_2,
                "required_new_control_date": required_new_control_date,
                "evaluation_date": evaluation_date,
            }
            out_dir = Path("files/system/students")
            out_dir.mkdir(parents=True, exist_ok=True)
            safe_name = re.sub(r'[^\w\s-]', '', (student_full_name or "interconsulta")).replace(" ", "_")[:30]
            out_file = out_dir / f"interconsulta_{safe_name}_{uuid.uuid4().hex[:8]}.docx"
            # Si no seleccionó Otro en Procedencia, quitar el placeholder "Haz clic o pulse aquí..." del docx
            remove_placeholders = ["Haz clic o pulse aquí para escribir texto.", "Haz clic o pulse aquí para escribir texto"] if not procedence_other_display else None
            result = DocumentsClass.fill_docx_form(str(template_path), replacements, str(out_file), remove_literal_strings=remove_placeholders)
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None
                    }
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        # Si document_id = 27, generar documento de evaluación psicopedagógica (psychopedagogical_evaluation.docx)
        if document_id == 27:
            cognitive_chart_tmp: Optional[str] = None
            def _fmt_date_d27(val):
                if not val:
                    return ""
                try:
                    if isinstance(val, str):
                        dt = datetime.strptime(val.strip()[:10], "%Y-%m-%d").date()
                    elif hasattr(val, "date"):
                        dt = val.date() if callable(getattr(val, "date", None)) else val
                    else:
                        dt = val
                    return dt.strftime("%d/%m/%Y")
                except Exception:
                    return str(val) if val else ""

            def _psychoped_html_to_plain(val: Any) -> str:
                """Campos IV–VI pueden guardarse como HTML (editor enriquecido); Word usa texto plano."""
                s = str(val or "").strip()
                if not s or "<" not in s:
                    return s
                try:
                    from bs4 import BeautifulSoup

                    return BeautifulSoup(s, "html.parser").get_text("\n", strip=True)
                except Exception:
                    import re

                    return re.sub(r"<[^>]+>", " ", s).strip()

            psychoped_service = PsychopedagogicalEvaluationClass(db)
            psychoped_result = psychoped_service.get_by_student_id(student_id=student_id, latest_only=True)
            eval_data = psychoped_result.get("data") if psychoped_result.get("status") == "success" else None
            if not eval_data:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None
                    }
                )

            student_data = student_result.get("student_data", {}) if isinstance(student_result, dict) else {}
            personal = student_data.get("personal_data") or {}
            academic = student_data.get("academic_info") or {}

            student_full_name = (
                f"{personal.get('names') or ''} {personal.get('father_lastname') or ''} {personal.get('mother_lastname') or ''}".strip()
                or eval_data.get("social_name")
                or f"Estudiante {student_id}"
            )
            student_social_name = str(eval_data.get("social_name") or "").strip() or student_full_name
            birth_day = _fmt_date_d27(personal.get("born_date"))
            student_age = str(eval_data.get("age") or "").strip()
            if not student_age and personal.get("born_date"):
                try:
                    bd = personal.get("born_date")
                    if isinstance(bd, str):
                        bd = datetime.strptime(bd.strip()[:10], "%Y-%m-%d").date()
                    today = date.today()
                    years = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
                    student_age = f"{years} año(s)" if years != 1 else "1 año"
                except Exception:
                    pass
            student_school = ""
            student_obj = db.query(StudentModel).filter(StudentModel.id == student_id).first()
            if student_obj and student_obj.school_id:
                school = db.query(SchoolModel).filter(SchoolModel.id == student_obj.school_id).first()
                if school and school.school_name:
                    student_school = school.school_name
            student_course = ""
            if academic and academic.get("course_id"):
                course = db.query(CourseModel).filter(CourseModel.id == academic.get("course_id")).first()
                if course and course.course_name:
                    student_course = course.course_name
            evaluation_date = _fmt_date_d27(eval_data.get("evaluation_date"))
            diagnostic = str(eval_data.get("diagnosis") or "").strip()
            issue_date = _fmt_date_d27(eval_data.get("diagnosis_issue_date"))

            # admission_type_1..3: columna del motivo (INGRESO / REEVALUACIÓN / OTRO). Texto libre en
            # admission_type_other; si solo está marcada la opción, se muestra X para que el Word no quede vacío.
            admission_type_raw = str(eval_data.get("admission_type") or "").strip().lower()
            admission_type_key = "".join(
                c
                for c in unicodedata.normalize("NFKD", admission_type_raw)
                if unicodedata.category(c) != "Mn"
            )
            admission_type_other_val = str(eval_data.get("admission_type_other") or "").strip()
            admission_type_1 = ""
            admission_type_2 = ""
            admission_type_3 = ""
            if admission_type_key in ("ingreso", "1"):
                admission_type_1 = admission_type_other_val or "X"
            elif admission_type_key in ("reevaluacion", "2"):
                admission_type_2 = admission_type_other_val or "X"
            elif admission_type_key in ("otro", "other", "3"):
                admission_type_3 = admission_type_other_val or "X"

            instruments_applied = str(eval_data.get("instruments_applied") or "").strip()
            school_history_background = str(eval_data.get("school_history_background") or "").strip()
            cognitive_analysis = _psychoped_html_to_plain(eval_data.get("cognitive_analysis"))
            cognitive_chart_placeholder_text = ""
            inject_ac_table = False
            parsed_cq = parse_evalua_psychoped_matrices(eval_data)
            if parsed_cq and parsed_cq.has_table_numbers():
                inject_ac_table = True
                if parsed_cq.has_chart_numbers():
                    cognitive_chart_placeholder_text = CHART_PLACEHOLDER
                    fd, tmp_png = tempfile.mkstemp(suffix=".png")
                    os.close(fd)
                    if render_evalua_pt_line_chart_png(parsed_cq, tmp_png):
                        cognitive_chart_tmp = tmp_png
                    else:
                        try:
                            os.unlink(tmp_png)
                        except OSError:
                            pass
                        cognitive_chart_placeholder_text = ""
            personal_analysis = _psychoped_html_to_plain(eval_data.get("personal_analysis"))
            motor_analysis = _psychoped_html_to_plain(eval_data.get("motor_analysis"))
            conclusion = _psychoped_html_to_plain(eval_data.get("conclusion"))
            cognitive_synthesis = _psychoped_html_to_plain(eval_data.get("cognitive_synthesis"))
            personal_synthesis = _psychoped_html_to_plain(eval_data.get("personal_synthesis"))
            motor_synthesis = _psychoped_html_to_plain(eval_data.get("motor_synthesis"))
            suggestions_to_school = _psychoped_html_to_plain(eval_data.get("suggestions_to_school"))
            suggestions_to_classroom_team = _psychoped_html_to_plain(eval_data.get("suggestions_to_classroom_team"))
            suggestions_to_family = _psychoped_html_to_plain(eval_data.get("suggestions_to_family"))
            suggestions_to_student = _psychoped_html_to_plain(eval_data.get("suggestions_to_student"))
            other_suggestions = _psychoped_html_to_plain(eval_data.get("other_suggestions"))

            professional_full_name = ""
            professional_identification_number = ""
            professional_registration_number = str(eval_data.get("professional_registration_number") or "").strip()
            professional_specialty = str(eval_data.get("professional_specialty") or "").strip()
            if eval_data.get("professional_id"):
                prof = db.query(ProfessionalModel).filter(ProfessionalModel.id == eval_data.get("professional_id")).first()
                if prof:
                    professional_full_name = f"{prof.names or ''} {prof.lastnames or ''}".strip()
                    professional_identification_number = str(prof.identification_number or "").strip()

            # Escalas: scale_{fila}_{columna} fila 1..10, columna 1..4 (1=valor "1", 2="2", 3="3", 4="N/O")
            scales_list = eval_data.get("scales") or []
            ped_by_indicator = {}
            soc_by_indicator = {}
            for s in scales_list:
                st = (s.get("scale_type") or "").strip().lower()
                ind = s.get("indicator_number")
                if ind is None:
                    continue
                try:
                    ind = int(ind)
                except (TypeError, ValueError):
                    continue
                val = (s.get("value") or "").strip().upper()
                if not val:
                    continue
                if "social" in st or "comunica" in st or st == "social_communicative":
                    soc_by_indicator[ind] = val
                else:
                    ped_by_indicator[ind] = val

            def _value_to_col(v):
                if v in ("1",):
                    return 1
                if v in ("2",):
                    return 2
                if v in ("3",):
                    return 3
                if v in ("N/O", "NO", "N-O"):
                    return 4
                return None

            replacements = {
                "student_full_name": student_full_name,
                "student_social_name": student_social_name,
                "birth_day": birth_day,
                "student_age": student_age,
                "student_school": student_school,
                "student_course": student_course,
                "evaluation_date": evaluation_date,
                "diagnostic": diagnostic,
                "issue_date": issue_date,
                "admission_type_1": admission_type_1,
                "admission_type_2": admission_type_2,
                "admission_type_3": admission_type_3,
                "instruments_applied": instruments_applied,
                "school_history_background": school_history_background,
                "cognitive_analysis": cognitive_analysis,
                "ac": AC_CONTENT_CONTROL_HOLD if inject_ac_table else "",
                "acg": cognitive_chart_placeholder_text,
                "personal_analysis": personal_analysis,
                "motor_analysis": motor_analysis,
                "conclusion": conclusion,
                "cognitive_synthesis": cognitive_synthesis,
                "personal_synthesis": personal_synthesis,
                "motor_synthesis": motor_synthesis,
                "suggestions_to_school": suggestions_to_school,
                "suggestions_to_classroom_team": suggestions_to_classroom_team,
                "suggestions_to_family": suggestions_to_family,
                "suggestions_to_student": suggestions_to_student,
                "other_suggestions": other_suggestions,
                "professional_full_name": professional_full_name,
                "professional_identification_number": professional_identification_number,
                "professional_registration_number": professional_registration_number,
                "professional_specialty": professional_specialty,
            }
            # Etiquetas de controles de contenido en Word (a menudo en español / distinto snake_case)
            # → claves usadas en `replacements`. Clave = tag normalizado (minúsculas, sin tildes, guiones bajos).
            psychoped_content_control_aliases = {
                "nombre_identidad_estudiante": "student_full_name",
                "nombre_de_identidad_estudiante": "student_full_name",
                "nombre_identidad_del_estudiante": "student_full_name",
                "nombre_completo_estudiante": "student_full_name",
                "nombre_y_apellidos_del_estudiante": "student_full_name",
                "nombre_social_del_estudiante": "student_social_name",
                "nombre_social_estudiante": "student_social_name",
                "nombre_social": "student_social_name",
                "fecha_de_nacimiento": "birth_day",
                "fecha_nacimiento": "birth_day",
                "edad": "student_age",
                "edad_del_estudiante": "student_age",
                "establecimiento_educacional": "student_school",
                "establecimiento": "student_school",
                "nombre_establecimiento": "student_school",
                "colegio": "student_school",
                "curso_nivel": "student_course",
                "curso_o_nivel": "student_course",
                "curso": "student_course",
                "nivel": "student_course",
                "fecha_de_evaluacion": "evaluation_date",
                "fecha_evaluacion": "evaluation_date",
                "diagnostico": "diagnostic",
                "diagnosis": "diagnostic",
                "fecha_de_emision_de_diagnostico": "issue_date",
                "fecha_emision_diagnostico": "issue_date",
                "fecha_emision_del_diagnostico": "issue_date",
                "fecha_emision_de_diagnostico": "issue_date",
                "analisis_cognitivo": "cognitive_analysis",
                "analisis_cognitivo_comunicativo": "cognitive_analysis",
                "ac": "ac",
                "acg": "acg",
                "analisis_personal_socioemocional": "personal_analysis",
                "analisis_motor_autonomia_sensorial": "motor_analysis",
                "sintesis_cognitiva": "cognitive_synthesis",
                "sintesis_personal": "personal_synthesis",
                "sintesis_motora": "motor_synthesis",
                "sugerencias_al_establecimiento": "suggestions_to_school",
                "sugerencias_al_equipo_de_aula": "suggestions_to_classroom_team",
                "sugerencias_al_estudiante": "suggestions_to_student",
                "sugerencias_a_la_familia": "suggestions_to_family",
                "otras_sugerencias": "other_suggestions",
                "conclusion_informe": "conclusion",
                "instrumentos_aplicados": "instruments_applied",
                "antecedentes_historia_escolar": "school_history_background",
                "nombre_profesional": "professional_full_name",
                "rut_profesional": "professional_identification_number",
                "registro_profesional": "professional_registration_number",
                "especialidad_profesional": "professional_specialty",
            }
            # Pedagógica: filas 1 a 10
            for row in range(1, 11):
                for col in range(1, 5):
                    key = f"scale_{row}_{col}"
                    val_ped = ped_by_indicator.get(row)
                    c = _value_to_col(val_ped) if val_ped else None
                    replacements[key] = "X" if c == col else ""
            # Social/comunicativa: scale_11_1 .. scale_20_4; en BD vienen como indicador 1..10 → mapear a fila 11..20
            for row in range(11, 21):
                for col in range(1, 5):
                    key = f"scale_{row}_{col}"
                    social_indicator = row - 10  # indicador 1→fila11, 2→fila12, ... 10→fila20
                    val_soc = soc_by_indicator.get(social_indicator)
                    c = _value_to_col(val_soc) if val_soc else None
                    replacements[key] = "X" if c == col else ""

            template_path = Path("files/original_student_files") / "psychopedagogical_evaluation.docx"
            if not template_path.exists():
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": "Plantilla psychopedagogical_evaluation.docx no encontrada en files/original_student_files",
                        "data": None
                    }
                )
            out_dir = Path("files/system/students")
            out_dir.mkdir(parents=True, exist_ok=True)
            safe_name = re.sub(r'[^\w\s-]', '', (student_full_name or "evaluacion_psico")).replace(" ", "_")[:30]
            out_file = out_dir / f"evaluacion_psicopedagogica_{safe_name}_{uuid.uuid4().hex[:8]}.docx"
            psychoped_remove_placeholders = [
                "Haz clic o pulse aquí para escribir texto.",
                "Haz clic o pulse aquí para escribir texto",
                "Pulse o haga clic aquí para escribir texto.",
                "Haga clic aquí para escribir texto.",
            ]
            result = DocumentsClass.fill_docx_form(
                str(template_path),
                replacements,
                str(out_file),
                remove_literal_strings=psychoped_remove_placeholders,
                content_control_tag_aliases=psychoped_content_control_aliases,
            )
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None
                    }
                )
            out_path = result.get("file_path")
            if out_path and inject_ac_table and parsed_cq:
                inject_evalua_matrix_word_table(str(out_path), parsed_cq)
            if cognitive_chart_tmp and out_path:
                try:
                    if not insert_chart_placeholder_paragraph_image(str(out_path), cognitive_chart_tmp):
                        strip_chart_placeholder_from_docx(str(out_path))
                finally:
                    try:
                        os.unlink(cognitive_chart_tmp)
                    except OSError:
                        pass
            elif out_path and CHART_PLACEHOLDER in (replacements.get("acg") or ""):
                strip_chart_placeholder_from_docx(str(out_path))
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
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
                        "message": MSG_NO_DOC,
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
                        "message": result.get("message", MSG_ERROR_GEN),
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
                        "message": MSG_NO_DOC,
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
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None,
                    },
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf",
            )
        
        # Si document_id = 20, generar documento CESP (Plan de Acompañamiento Emocional y Conductual - PAEC)
        if document_id == 20:
            cesp_service = CespClass(db)
            cesp_result = cesp_service.get_by_student_id(student_id, latest_only=True)
            if isinstance(cesp_result, dict) and cesp_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"status": 404, "message": MSG_NO_DOC, "data": None},
                )
            cesp_data_raw = cesp_result.get("data") if isinstance(cesp_result, dict) else None
            if not cesp_data_raw or not isinstance(cesp_data_raw, dict):
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"status": 404, "message": MSG_NO_DOC, "data": None},
                )
            student_data = student_result.get("student_data", {}) if isinstance(student_result, dict) else {}
            personal_data = student_data.get("personal_data") or {}
            academic_info = student_data.get("academic_info") or {}
            student_name = personal_data.get("names", "") or ""
            student_lastname = f"{personal_data.get('father_lastname', '')} {personal_data.get('mother_lastname', '')}".strip()
            student_fullname = f"{student_name} {student_lastname}".strip()
            cesp_data = dict(cesp_data_raw)
            cesp_data["student_fullname"] = student_fullname
            cesp_data["student_name"] = student_name
            cesp_data["student_lastname"] = student_lastname
            # Datos personales o generales para el PDF
            cesp_data["student_rut"] = personal_data.get("identification_number", "") or ""
            cesp_data["student_born_date"] = personal_data.get("born_date", "") or cesp_data_raw.get("student_born_date", "")
            school_name = cesp_data_raw.get("student_school") or student_data.get("school_name") or ""
            if not school_name and student_data.get("school_id"):
                school = db.query(SchoolModel).filter(SchoolModel.id == student_data["school_id"]).first()
                if school:
                    school_name = (school.school_name or "").strip()
            course_name = cesp_data_raw.get("student_course") or (academic_info.get("course_name") if isinstance(academic_info, dict) else "") or ""
            if not course_name and academic_info and isinstance(academic_info, dict) and academic_info.get("course_id"):
                course = db.query(CourseModel).filter(CourseModel.id == academic_info["course_id"]).first()
                if course:
                    course_name = (course.course_name or "").strip()
            nee_name = cesp_data_raw.get("student_nee") or ""
            if not nee_name and academic_info and isinstance(academic_info, dict):
                nee_name = (academic_info.get("special_educational_need_name") or "").strip() or (academic_info.get("special_educational_needs") or "").strip()
            cesp_data["student_school"] = school_name
            cesp_data["student_course"] = course_name
            cesp_data["student_nee"] = nee_name or str(cesp_data_raw.get("student_nee") or "")
            # Edad calculada desde fecha de nacimiento
            student_age = ""
            born_date_str = cesp_data.get("student_born_date", "")
            if born_date_str:
                try:
                    born_date = None
                    for date_fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"]:
                        try:
                            born_date = datetime.strptime(str(born_date_str)[:10], date_fmt).date()
                            break
                        except Exception:
                            continue
                    if born_date:
                        ref = datetime.now().date()
                        years = ref.year - born_date.year
                        months = ref.month - born_date.month
                        if months < 0:
                            years -= 1
                            months += 12
                        elif months == 0 and ref.day < born_date.day:
                            years -= 1
                            months = 11
                        if years > 0:
                            student_age = f"{years} año{'s' if years != 1 else ''} y {months} mes{'es' if months != 1 else ''}" if months else f"{years} año{'s' if years != 1 else ''}"
                        elif months > 0:
                            student_age = f"{months} mes{'es' if months != 1 else ''}"
                except Exception:
                    pass
            cesp_data["student_age"] = student_age
            participant = cesp_data.get("participant_professional")
            if participant and isinstance(participant, dict) and participant.get("professional_id"):
                prof = db.query(ProfessionalModel).filter(ProfessionalModel.id == participant["professional_id"]).first()
                cesp_data["participant_professional_name"] = f"{prof.names or ''} {prof.lastnames or ''}".strip() if prof else ""
            support_list = cesp_data.get("support_team_members") or []
            for s in support_list:
                if isinstance(s, dict) and s.get("professional_id"):
                    prof = db.query(ProfessionalModel).filter(ProfessionalModel.id == s["professional_id"]).first()
                    s["professional_name"] = f"{prof.names or ''} {prof.lastnames or ''}".strip() if prof else ""
            # Registros DEC (incidentes de acción) del estudiante para sección VII
            incidents_result = ActionIncidentClass(db).get_all(student_id=student_id)
            dec_records = []
            if isinstance(incidents_result, list):
                dec_records = incidents_result
            elif isinstance(incidents_result, dict) and incidents_result.get("data"):
                dec_records = incidents_result.get("data", [])
            cesp_data["dec_records"] = dec_records
            result = DocumentsClass.generate_document_pdf(
                document_id=document_id,
                document_data=cesp_data,
                db=db,
                template_path=None,
                output_directory="files/system/students",
            )
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"status": 500, "message": result.get("message", MSG_ERROR_GEN), "data": None},
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
                        "message": MSG_NO_DOC,
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
                        "message": result.get("message", MSG_ERROR_GEN),
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
                        "message": MSG_NO_DOC,
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
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None
                    }
                )
            
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type='application/pdf'
            )
        
        # Si document_id = 9, generar Informe fonoaudiológico IDTEL desde cero
        if document_id == 9:
            idtel_service = IdtelReportClass(db)
            idtel_result = idtel_service.get_by_student_id(student_id)
            if isinstance(idtel_result, dict) and idtel_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None
                    }
                )
            report_data = idtel_result.copy() if isinstance(idtel_result, dict) else {}
            report_data.pop("id", None)
            report_data.pop("added_date", None)
            report_data.pop("updated_date", None)
            if report_data.get("course_id"):
                course = db.query(CourseModel).filter(CourseModel.id == report_data["course_id"]).first()
                if course and course.course_name:
                    report_data["course_name"] = course.course_name
                report_data.pop("course_id", None)
            else:
                report_data["course_name"] = report_data.get("course_name") or ""
            estab = report_data.get("establishment_id")
            if estab is not None and str(estab).strip().isdigit():
                try:
                    sid = int(estab)
                    school = db.query(SchoolModel).filter(SchoolModel.id == sid).first()
                    if school and school.school_name:
                        report_data["establishment_id"] = school.school_name
                except (ValueError, TypeError):
                    pass
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
                document_id=9,
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
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None
                    }
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf"
            )

        # Informe de evaluación psicomotriz (catálogo por nombre en `documents`)
        if _catalog_row_is_informe_evaluacion_psicomotriz(document_id, db):
            psico_service = PsychomotorEvaluationReportClass(db)
            psico_result = psico_service.get_by_student_id(student_id)
            if isinstance(psico_result, dict) and psico_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None
                    }
                )
            report_data = psico_result.copy() if isinstance(psico_result, dict) else {}
            report_data.pop("id", None)
            report_data.pop("added_date", None)
            report_data.pop("updated_date", None)
            if report_data.get("course_id"):
                course = db.query(CourseModel).filter(CourseModel.id == report_data["course_id"]).first()
                if course and course.course_name:
                    report_data["course_name"] = course.course_name
                report_data.pop("course_id", None)
            else:
                report_data["course_name"] = report_data.get("course_name") or ""
            estab = report_data.get("establishment_id")
            if estab is not None and str(estab).strip().isdigit():
                try:
                    sid = int(estab)
                    school = db.query(SchoolModel).filter(SchoolModel.id == sid).first()
                    if school and school.school_name:
                        report_data["establishment_id"] = school.school_name
                except (ValueError, TypeError):
                    pass
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
                document_id=document_id,
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
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None
                    }
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf"
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
                        "message": MSG_NO_DOC,
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
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None,
                    },
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf",
            )
        
        # Si document_id = 25, generar Certificado Ley TEA (PDF) desde cero; datos de tabla guardian_attendance_certificate
        if document_id == 25:
            gac_service = GuardianAttendanceCertificateClass(db)
            gac_data = gac_service.get_by_student_id(student_id)
            if isinstance(gac_data, dict) and gac_data.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None,
                    },
                )
            student_data = student_result.get("student_data", {}) if isinstance(student_result, dict) else {}
            personal = student_data.get("personal_data") or {}
            academic = student_data.get("academic_info") or {}
            _fn = f"{personal.get('names') or ''} {personal.get('father_lastname') or ''} {personal.get('mother_lastname') or ''}".strip()
            cert_data = {
                "student_full_name": _fn if _fn else f"Estudiante {student_id}",
                "establishment_name": "",
                "guardian_fullname": "",
                "guardian_rut": "",
                "course_name": "",
                "nee_name": "",
                "attendance_date": "",
                "attendance_time": "",
            }
            school_id = student_data.get("school_id")
            if school_id:
                school = db.query(SchoolModel).filter(SchoolModel.id == school_id).first()
                cert_data["establishment_name"] = school.school_name if school and school.school_name else ""
            course_id = academic.get("course_id")
            if course_id:
                course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
                cert_data["course_name"] = course.course_name if course and course.course_name else ""
            nee_id = academic.get("special_educational_need_id")
            if nee_id:
                nee = db.query(SpecialEducationalNeedModel).filter(SpecialEducationalNeedModel.id == nee_id).first()
                cert_data["nee_name"] = nee.special_educational_needs if nee and nee.special_educational_needs else ""
            g = db.query(StudentGuardianModel).filter(StudentGuardianModel.student_id == student_id).order_by(StudentGuardianModel.id.desc()).first()
            if g:
                cert_data["guardian_fullname"] = f"{g.names or ''} {g.father_lastname or ''} {g.mother_lastname or ''}".strip()
                cert_data["guardian_rut"] = g.identification_number or ""
            # Fecha y horario solo desde guardian_attendance_certificate (tabla del documento 25)
            _cd = gac_data.get("certificate_date")
            if _cd:
                try:
                    if isinstance(_cd, str) and len(_cd) >= 10:
                        d = datetime.strptime(_cd[:10], "%Y-%m-%d").date()
                        cert_data["attendance_date"] = d.strftime("%d/%m/%Y")
                    elif hasattr(_cd, "strftime"):
                        cert_data["attendance_date"] = _cd.strftime("%d/%m/%Y")
                except Exception:
                    cert_data["attendance_date"] = str(_cd)[:10] if _cd else ""
            _st = gac_data.get("start_time") or ""
            _et = gac_data.get("end_time") or ""
            if _st and _et:
                cert_data["attendance_time"] = f"{_st} a {_et}".strip()
            elif _st:
                cert_data["attendance_time"] = str(_st).strip()
            else:
                cert_data["attendance_time"] = str(_et).strip()
            result = DocumentsClass.generate_document_pdf(
                document_id=25,
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
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None,
                    },
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf",
            )
        
        # Si document_id = 29, generar Test de Conners (PDF) desde cero; datos de conners_teacher_evaluations
        if document_id == 29:
            conners_service = ConnersTeacherEvaluationClass(db)
            conners_result = conners_service.get_by_student_id(student_id, latest_only=True)
            if not conners_result or conners_result.get("status") != "success" or not conners_result.get("data"):
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None,
                    },
                )
            eval_data = conners_result["data"]
            student_data = student_result.get("student_data", {}) if isinstance(student_result, dict) else {}
            personal = student_data.get("personal_data") or {}
            student_full_name = f"{personal.get('names') or ''} {personal.get('father_lastname') or ''} {personal.get('mother_lastname') or ''}".strip()
            if not student_full_name:
                student_full_name = f"Estudiante {student_id}"
            student_rut = student_data.get("identification_number") or personal.get("identification_number") or ""
            born_raw = personal.get("born_date") or student_data.get("born_date")
            student_born_date = ""
            if born_raw:
                try:
                    s = str(born_raw).strip()[:10]
                    if len(s) == 10 and s[4] == "-" and s[7] == "-":
                        d = datetime.strptime(s, "%Y-%m-%d").date()
                        student_born_date = d.strftime("%d/%m/%Y")
                    else:
                        student_born_date = s
                except Exception:
                    student_born_date = str(born_raw)[:10] if born_raw else ""
            conners_data = {
                "student_full_name": student_full_name,
                "student_rut": student_rut,
                "student_born_date": student_born_date,
                "evaluation_date": eval_data.get("evaluation_date") or "",
                "evaluator_name": eval_data.get("evaluator_name") or "",
                "evaluation_type": eval_data.get("evaluation_type") or "ingreso",
                "comments_observations": eval_data.get("comments_observations") or "",
                "total_score": eval_data.get("total_score"),
                "scores": eval_data.get("scores") or [],
                "conduct_responses": eval_data.get("conduct_responses") or [],
            }
            result = DocumentsClass.generate_document_pdf(
                document_id=29,
                document_data=conners_data,
                db=db,
                template_path=None,
                output_directory="files/system/students",
            )
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None,
                    },
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf",
            )
        
        # Si document_id = 31, generar Pauta de evaluación pedagógica - Docente de aula - 1º Básico (PDF)
        if document_id == 31:
            pe_service = PedagogicalEvaluationClassroomFirstGradeClass(db)
            pe_result = pe_service.get_by_student_id(student_id)
            if isinstance(pe_result, dict) and pe_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None,
                    },
                )
            doc_data_31 = dict(pe_result)
            result = DocumentsClass.generate_document_pdf(
                document_id=31,
                document_data=doc_data_31,
                db=db,
                template_path=None,
                output_directory="files/system/students",
            )
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None,
                    },
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf",
            )
        
        # Si document_id = 32, generar Pauta de evaluación pedagógica - Docente de aula - 2º Básico (PDF)
        if document_id == 32:
            pe2_service = PedagogicalEvaluationClassroomSecondGradeClass(db)
            pe2_result = pe2_service.get_by_student_id(student_id)
            if isinstance(pe2_result, dict) and pe2_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None,
                    },
                )
            doc_data_32 = dict(pe2_result)
            result = DocumentsClass.generate_document_pdf(
                document_id=32,
                document_data=doc_data_32,
                db=db,
                template_path=None,
                output_directory="files/system/students",
            )
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None,
                    },
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf",
            )
        
        # Si document_id = 33, generar Pauta de evaluación pedagógica - Docente de aula - 3º Básico (PDF)
        if document_id == 33:
            pe3_service = PedagogicalEvaluationClassroomThirdGradeClass(db)
            pe3_result = pe3_service.get_by_student_id(student_id)
            if isinstance(pe3_result, dict) and pe3_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None,
                    },
                )
            doc_data_33 = dict(pe3_result)
            result = DocumentsClass.generate_document_pdf(
                document_id=33,
                document_data=doc_data_33,
                db=db,
                template_path=None,
                output_directory="files/system/students",
            )
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None,
                    },
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf",
            )
        
        # Si document_id = 34, generar Pauta de evaluacion pedagogica - Docente de aula - 4to Basico (PDF)
        if document_id == 34:
            pe4_service = PedagogicalEvaluationClassroomFourthGradeClass(db)
            pe4_result = pe4_service.get_by_student_id(student_id)
            if isinstance(pe4_result, dict) and pe4_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None,
                    },
                )
            doc_data_34 = dict(pe4_result)
            result = DocumentsClass.generate_document_pdf(
                document_id=34,
                document_data=doc_data_34,
                db=db,
                template_path=None,
                output_directory="files/system/students",
            )
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None,
                    },
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf",
            )
        
        # Si document_id = 35, generar Pauta de evaluacion pedagogica - Docente de aula - 5to Basico (PDF)
        if document_id == 35:
            pe5_service = PedagogicalEvaluationClassroomFifthGradeClass(db)
            pe5_result = pe5_service.get_by_student_id(student_id)
            if isinstance(pe5_result, dict) and pe5_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None,
                    },
                )
            doc_data_35 = dict(pe5_result)
            result = DocumentsClass.generate_document_pdf(
                document_id=35,
                document_data=doc_data_35,
                db=db,
                template_path=None,
                output_directory="files/system/students",
            )
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None,
                    },
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf",
            )
        
        # Si document_id = 36, generar Pauta de evaluacion pedagogica - Docente de aula - 6to Basico (PDF)
        if document_id == 36:
            pe6_service = PedagogicalEvaluationClassroomSixthGradeClass(db)
            pe6_result = pe6_service.get_by_student_id(student_id)
            if isinstance(pe6_result, dict) and pe6_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None,
                    },
                )
            doc_data_36 = dict(pe6_result)
            result = DocumentsClass.generate_document_pdf(
                document_id=36,
                document_data=doc_data_36,
                db=db,
                template_path=None,
                output_directory="files/system/students",
            )
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None,
                    },
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf",
            )
        
        # Si document_id = 37, generar Pauta de evaluacion pedagogica - Docente de aula - 7mo Basico (PDF)
        if document_id == 37:
            pe7_service = PedagogicalEvaluationClassroomSeventhGradeClass(db)
            pe7_result = pe7_service.get_by_student_id(student_id)
            if isinstance(pe7_result, dict) and pe7_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None,
                    },
                )
            doc_data_37 = dict(pe7_result)
            result = DocumentsClass.generate_document_pdf(
                document_id=37,
                document_data=doc_data_37,
                db=db,
                template_path=None,
                output_directory="files/system/students",
            )
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None,
                    },
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf",
            )
        
        # Si document_id = 38, generar Pauta de evaluacion pedagogica - Docente de aula - 8vo Basico (PDF)
        if document_id == 38:
            pe8_service = PedagogicalEvaluationClassroomEighthGradeClass(db)
            pe8_result = pe8_service.get_by_student_id(student_id)
            if isinstance(pe8_result, dict) and pe8_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None,
                    },
                )
            doc_data_38 = dict(pe8_result)
            result = DocumentsClass.generate_document_pdf(
                document_id=38,
                document_data=doc_data_38,
                db=db,
                template_path=None,
                output_directory="files/system/students",
            )
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None,
                    },
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf",
            )
        
        # Si document_id = 39, generar Pauta de evaluacion pedagogica - Docente de aula - 1ero Medio (PDF)
        if document_id == 39:
            pe1s_service = PedagogicalEvaluationClassroomFirstGradeSecondaryClass(db)
            pe1s_result = pe1s_service.get_by_student_id(student_id)
            if isinstance(pe1s_result, dict) and pe1s_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None,
                    },
                )
            doc_data_39 = dict(pe1s_result)
            result = DocumentsClass.generate_document_pdf(
                document_id=39,
                document_data=doc_data_39,
                db=db,
                template_path=None,
                output_directory="files/system/students",
            )
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", MSG_ERROR_GEN),
                        "data": None,
                    },
                )
            return FileResponse(
                path=result["file_path"],
                filename=result["filename"],
                media_type="application/pdf",
            )
        
        # Si document_id = 40, generar Pauta de evaluacion pedagogica - Docente de aula - 2do Medio (PDF)
        if document_id == 40:
            pe2s_service = PedagogicalEvaluationClassroomSecondGradeSecondaryClass(db)
            pe2s_result = pe2s_service.get_by_student_id(student_id)
            if isinstance(pe2s_result, dict) and pe2s_result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "status": 404,
                        "message": MSG_NO_DOC,
                        "data": None,
                    },
                )
            doc_data_40 = dict(pe2s_result)
            result = DocumentsClass.generate_document_pdf(
                document_id=40,
                document_data=doc_data_40,
                db=db,
                template_path=None,
                output_directory="files/system/students",
            )
            if result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": result.get("message", MSG_ERROR_GEN),
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
                        "message": result.get("message", MSG_ERROR_GEN),
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
                        school_id=None,
                        course_id=None,
                        student_id=student_id,
                        document_id=parent_auth_document_id,  # document_id = 2 para parent_authorization
                        version_id=new_version_id,
                        detail_id=None,  # No hay detail_id para parent_authorization
                        professional_id=0,
                        file=unique_filename,
                        period_year=None,
                        added_date=datetime.now(),
                        updated_date=datetime.now(),
                        deleted_date=None,
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
                    "message": result.get("message", MSG_ERROR_GEN),
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
                "message": MSG_ERROR_GEN,
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


@documents.post("/fill-docx")
async def fill_docx_form(
    body: dict = Body(default={"template_name": "am.docx", "replacements": {"nombre": "Prueba"}}),
    session_user: UserLogin = Depends(get_current_active_user),
):
    """
    Prueba: rellena un formulario DOCX reemplazando etiquetas.
    Body: {"template_name": "am.docx", "replacements": {"nombre": "Juan", "fecha": "28/01/2026"}}
    Formatos soportados en DOCX: {etiqueta}, [etiqueta], <<etiqueta>>
    """
    try:
        template_name = body.get("template_name", "am.docx")
        replacements = body.get("replacements", {"nombre": "Prueba"})
        template_path = Path("files/original_student_files") / template_name
        if not template_path.exists():
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": f"Template no encontrado: {template_name}", "data": None},
            )
        out_dir = Path("files/system/students")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"docx_filled_{uuid.uuid4().hex[:8]}.docx"
        result = DocumentsClass.fill_docx_form(str(template_path), replacements, str(out_file))
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": 400, "message": result.get("message", "Error"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "DOCX rellenado correctamente",
                "data": {"filename": result.get("filename"), "file_path": result.get("file_path")},
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )
