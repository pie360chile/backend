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
from app.backend.routers.authentications import authentications
from app.backend.routers.rols import rols
from app.backend.routers.permissions import permissions
from app.backend.routers.settings import settings
from app.backend.routers.users import users
from app.backend.routers.teachings import teachings
from app.backend.routers.courses import courses
from app.backend.routers.communes import communes
from app.backend.routers.regions import regions
from app.backend.routers.native_language_proficiencies import native_language_proficiencies
from app.backend.routers.documents import documents
from app.backend.routers.family_members import family_members
from app.backend.routers.news import news
from app.backend.routers.nationalities import nationalities
from app.backend.routers.genders import genders
from app.backend.routers.schools import schools
from app.backend.routers.students import students
from app.backend.routers.customers import customers
from app.backend.routers.professionals import professionals
from app.backend.routers.packages import packages
from app.backend.routers.student_guardians import student_guardians
from app.backend.routers.special_educational_needs import special_educational_needs
from app.backend.routers.document_types import document_types
from app.backend.routers.messages import messages
from app.backend.routers.actions_incidents import actions_incidents
from app.backend.routers.downloads import downloads
from app.backend.routers.videos import videos
from app.backend.routers.career_types import career_types
from app.backend.routers.faqs import faqs
from app.backend.routers.contacts import contacts
from app.backend.routers.student_document_files import student_document_files
from app.backend.routers.folders import folders
from app.backend.routers.health_evaluations import health_evaluations
from app.backend.routers.artificial_intelligence import artificial_intelligence
from app.backend.routers.events import events
from app.backend.routers.bank_descriptions import bank_descriptions
from app.backend.routers.progress_status_students import progress_status_students
from app.backend.routers.individual_support_plans import individual_support_plans
from app.backend.routers.progress_status_individual_supports import progress_status_individual_supports
from app.backend.routers.fonoaudiological_reports import fonoaudiological_reports
from app.backend.routers.school_integration_program_exit_certificates import school_integration_program_exit_certificates
from app.backend.routers.audits import audits

app = FastAPI(root_path="/api")
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
app.include_router(nationalities)
app.include_router(genders)
app.include_router(schools)
app.include_router(students)
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
app.include_router(events)
app.include_router(bank_descriptions)
app.include_router(progress_status_students)
app.include_router(individual_support_plans)
app.include_router(progress_status_individual_supports)
app.include_router(fonoaudiological_reports)
app.include_router(school_integration_program_exit_certificates)
app.include_router(audits)

if __name__ == "__main__":
    # Para aumentar el límite de tamaño de archivo, configurar en el servidor
    # En producción con gunicorn, usar: --limit-request-line 8190 --limit-request-field_size 8190
    # El límite por defecto de Starlette es 1MB, se puede aumentar configurando el servidor
    uvicorn.run("main:app", port=8000, reload=True)
