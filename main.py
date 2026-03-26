from fastapi import FastAPI, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
import os
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from app.backend.routes.authentications import authentications
from app.backend.routes.rols import rols
from app.backend.routes.permissions import permissions
from app.backend.routes.settings import settings
from app.backend.routes.users import users
from app.backend.routes.teachings import teachings
from app.backend.routes.courses import courses
from app.backend.routes.communes import communes
from app.backend.routes.regions import regions
from app.backend.routes.native_language_proficiencies import native_language_proficiencies
from app.backend.routes.documents import documents
from app.backend.routes.family_members import family_members
from app.backend.routes.news import news
from app.backend.routes.external_api import external_api
from app.backend.routes.nationalities import nationalities
from app.backend.routes.genders import genders
from app.backend.routes.schools import schools
from app.backend.routes.students import students
from app.backend.routes.students_professionals import students_professionals
from app.backend.routes.document_alerts import document_alerts
from app.backend.routes.customers import customers
from app.backend.routes.professionals import professionals
from app.backend.routes.packages import packages
from app.backend.routes.student_guardians import student_guardians
from app.backend.routes.special_educational_needs import special_educational_needs
from app.backend.routes.document_types import document_types
from app.backend.routes.messages import messages
from app.backend.routes.actions_incidents import actions_incidents
from app.backend.routes.downloads import downloads
from app.backend.routes.videos import videos
from app.backend.routes.career_types import career_types
from app.backend.routes.faqs import faqs
from app.backend.routes.contacts import contacts
from app.backend.routes.student_document_files import student_document_files
from app.backend.routes.folders import folders
from app.backend.routes.health_evaluations import health_evaluations
from app.backend.routes.artificial_intelligence import artificial_intelligence
from app.backend.routes.evaluator_chat import evaluator_chat
from app.backend.routes.events import events
from app.backend.routes.bank_descriptions import bank_descriptions
from app.backend.routes.progress_status_students import progress_status_students
from app.backend.routes.individual_support_plans import individual_support_plans
from app.backend.routes.progress_status_individual_supports import progress_status_individual_supports
from app.backend.routes.fonoaudiological_reports import fonoaudiological_reports
from app.backend.routes.school_integration_program_exit_certificates import school_integration_program_exit_certificates
from app.backend.routes.audits import audits
from app.backend.routes.anamnesis import anamnesis
from app.backend.routes.family_reports import family_reports
from app.backend.routes.interconsultations import interconsultations
from app.backend.routes.guardian_attendance_certificates import guardian_attendance_certificates
from app.backend.routes.professional_teaching_courses import professional_teaching_courses
from app.backend.routes.professional_document_assignments import professional_document_assignments
from app.backend.routes.app_alerts import alerts
from app.backend.routes.kpi_document_assignments import kpi_document_assignments
from app.backend.routes.kpi_documentation_progress import kpi_documentation_progress
from app.backend.routes.coordinators_courses import coordinators_courses
from app.backend.routes.meeting_schedualings import meeting_schedualings
from app.backend.routes.meeting_schedualing_agreements import meeting_schedualing_agreements
from app.backend.routes.meeting_schedualing_register_professionals import meeting_schedualing_register_professionals
from app.backend.routes.diversified_strategies import diversified_strategies
from app.backend.routes.regular_teacher_diversified_strategies import regular_teacher_diversified_strategies
from app.backend.routes.subjects import subjects
from app.backend.routes.collaborative_works import collaborative_works
from app.backend.routes.support_organizations import support_organizations
from app.backend.routes.diversity_criteria import diversity_criteria
from app.backend.routes.diversity_strategy_options import diversity_strategy_options
from app.backend.routes.course_diversity_responses import course_diversity_responses
from app.backend.routes.course_adjustments import course_adjustments
from app.backend.routes.course_curricular_adequacies import course_curricular_adequacies
from app.backend.routes.course_individual_supports import course_individual_supports
from app.backend.routes.plan_apoyo_individual import plan_apoyo_individual
from app.backend.routes.course_eval_diversity import course_eval_diversity
from app.backend.routes.course_family_community import course_family_community
from app.backend.routes.support_areas import support_areas
from app.backend.routes.dynamic_forms import dynamic_forms
from app.backend.routes.differentiated_strategies_implementations import differentiated_strategies_implementations
from app.backend.routes.course_teacher_record_observations import course_teacher_record_observations
from app.backend.routes.course_teacher_record_activities import course_teacher_record_activities
from app.backend.routes.course_record_supports import course_record_supports
from app.backend.routes.course_learning_achievements import course_learning_achievements
from app.backend.routes.psychopedagogical_evaluations import psychopedagogical_evaluations
from app.backend.routes.conners_teacher_evaluations import conners_teacher_evaluations
from app.backend.routes.diagnosis_summary import diagnosis_summary
from app.backend.routes.cesp import cesp
from app.backend.routes.idtel_reports import idtel_reports
from app.backend.routes.pedagogical_evaluation_classroom_first_grade import pedagogical_evaluation_classroom_first_grade
from app.backend.routes.pedagogical_evaluation_classroom_second_grade import pedagogical_evaluation_classroom_second_grade
from app.backend.routes.pedagogical_evaluation_classroom_third_grade import pedagogical_evaluation_classroom_third_grade
from app.backend.routes.pedagogical_evaluation_classroom_fourth_grade import pedagogical_evaluation_classroom_fourth_grade
from app.backend.routes.pedagogical_evaluation_classroom_fifth_grade import pedagogical_evaluation_classroom_fifth_grade
from app.backend.routes.pedagogical_evaluation_classroom_sixth_grade import pedagogical_evaluation_classroom_sixth_grade
from app.backend.routes.pedagogical_evaluation_classroom_seventh_grade import pedagogical_evaluation_classroom_seventh_grade
from app.backend.routes.pedagogical_evaluation_classroom_eighth_grade import pedagogical_evaluation_classroom_eighth_grade
from app.backend.routes.pedagogical_evaluation_classroom_first_grade_secondary import pedagogical_evaluation_classroom_first_grade_secondary
from app.backend.routes.pedagogical_evaluation_classroom_second_grade_secondary import pedagogical_evaluation_classroom_second_grade_secondary

# OpenAPI (Swagger): FastAPI genera automáticamente el esquema desde rutas y modelos Pydantic.
# Documentación interactiva:
#   - Swagger UI:  http://localhost:8005/docs     (o /api/docs si usas proxy con root_path)
#   - ReDoc:       http://localhost:8005/redoc    (o /api/redoc)
#   - JSON schema: http://localhost:8005/openapi.json
app = FastAPI(
    root_path="/api",
    title="PIE 360 API",
    description="API del proyecto PIE 360",
    version="1.0.0",
    docs_url="/docs",       # Swagger UI (poner None para desactivar)
    redoc_url="/redoc",     # ReDoc (poner None para desactivar)
    openapi_url="/openapi.json",  # Esquema OpenAPI en JSON
)
application = app

# Nota: El límite de tamaño de archivo se configura en el servidor
# Para uvicorn en desarrollo, el límite por defecto es ~1MB
# Para aumentar en producción con gunicorn, agregar a la configuración:
# --limit-request-line 8190 --limit-request-field_size 8190
# O configurar en el archivo de servicio systemd/service

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "message": exc.detail,
            "data": None
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": 500,
            "message": f"Internal server error: {str(exc)}",
            "data": None
        }
    )

# Usar variable de entorno o ruta por defecto según el entorno
FILES_DIR = os.environ.get('FILES_DIR', '/var/www/pie360backend.cl/public_html/files')

Path(FILES_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")

os.environ['SECRET_KEY'] = '7de4c36b48fce8dcb3a4bb527ba62d789ebf3d3a7582472ee49d430b01a7f868'
os.environ['ALGORITHM'] = 'HS256'

origins = [
    "*",
    "https://newerp-ghdegyc9cpcpc6gq.eastus-01.azurewebsites.net",
    
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def period_year_middleware(request: Request, call_next):
    """Expone `period_year` del query string en `request.state.period_year` (útil en routes)."""
    raw = request.query_params.get("period_year")
    if raw is not None and str(raw).strip() != "":
        try:
            request.state.period_year = int(raw)
        except ValueError:
            request.state.period_year = None
    else:
        request.state.period_year = None
    return await call_next(request)


app.include_router(authentications)
app.include_router(rols)
app.include_router(permissions)
app.include_router(settings)
app.include_router(users)
app.include_router(teachings)
app.include_router(courses)
app.include_router(communes)
app.include_router(regions)
app.include_router(native_language_proficiencies)
app.include_router(documents)
app.include_router(family_members)
app.include_router(news)
app.include_router(external_api)
app.include_router(nationalities)
app.include_router(genders)
app.include_router(schools)
app.include_router(students)
app.include_router(students_professionals)
app.include_router(document_alerts)
app.include_router(customers)
app.include_router(professionals)
app.include_router(packages)
app.include_router(student_guardians)
app.include_router(special_educational_needs)
app.include_router(document_types)
app.include_router(messages)
app.include_router(actions_incidents)
app.include_router(downloads)
app.include_router(videos)
app.include_router(career_types)
app.include_router(faqs)
app.include_router(contacts)
app.include_router(student_document_files)
app.include_router(folders)
app.include_router(health_evaluations)
app.include_router(artificial_intelligence)
app.include_router(evaluator_chat)
app.include_router(events)
app.include_router(bank_descriptions)
app.include_router(progress_status_students)
app.include_router(individual_support_plans)
app.include_router(progress_status_individual_supports)
app.include_router(fonoaudiological_reports)
app.include_router(school_integration_program_exit_certificates)
app.include_router(audits)
app.include_router(anamnesis)
app.include_router(family_reports)
app.include_router(interconsultations)
app.include_router(guardian_attendance_certificates)
app.include_router(professional_teaching_courses)
app.include_router(professional_document_assignments)
app.include_router(alerts)
app.include_router(kpi_document_assignments)
app.include_router(kpi_documentation_progress)
app.include_router(coordinators_courses)
app.include_router(meeting_schedualings)
app.include_router(meeting_schedualing_agreements)
app.include_router(meeting_schedualing_register_professionals)
app.include_router(diversified_strategies)
app.include_router(regular_teacher_diversified_strategies)
app.include_router(subjects)
app.include_router(collaborative_works)
app.include_router(support_organizations)
app.include_router(diversity_criteria)
app.include_router(diversity_strategy_options)
app.include_router(course_diversity_responses)
app.include_router(course_adjustments)
app.include_router(course_curricular_adequacies)
app.include_router(course_individual_supports)
app.include_router(plan_apoyo_individual)
app.include_router(course_eval_diversity)
app.include_router(course_family_community)
app.include_router(support_areas)
app.include_router(dynamic_forms)
app.include_router(differentiated_strategies_implementations)
app.include_router(course_teacher_record_observations)
app.include_router(course_teacher_record_activities)
app.include_router(course_record_supports)
app.include_router(course_learning_achievements)
app.include_router(psychopedagogical_evaluations)
app.include_router(conners_teacher_evaluations)
app.include_router(diagnosis_summary)
app.include_router(cesp)
app.include_router(idtel_reports)
app.include_router(pedagogical_evaluation_classroom_first_grade)
app.include_router(pedagogical_evaluation_classroom_second_grade)
app.include_router(pedagogical_evaluation_classroom_third_grade)
app.include_router(pedagogical_evaluation_classroom_fourth_grade)
app.include_router(pedagogical_evaluation_classroom_fifth_grade)
app.include_router(pedagogical_evaluation_classroom_sixth_grade)
app.include_router(pedagogical_evaluation_classroom_seventh_grade)
app.include_router(pedagogical_evaluation_classroom_eighth_grade)
app.include_router(pedagogical_evaluation_classroom_first_grade_secondary)
app.include_router(pedagogical_evaluation_classroom_second_grade_secondary)

if __name__ == "__main__":
    # Para aumentar el límite de tamaño de archivo, configurar en el servidor
    # En producción con gunicorn, usar: --limit-request-line 8190 --limit-request-field_size 8190
    # El límite por defecto de Starlette es 1MB, se puede aumentar configurando el servidor
    uvicorn.run("main:app", port=8005, reload=True)
