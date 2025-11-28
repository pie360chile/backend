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

if __name__ == "__main__":
    # Para aumentar el límite de tamaño de archivo, configurar en el servidor
    # En producción con gunicorn, usar: --limit-request-line 8190 --limit-request-field_size 8190
    # El límite por defecto de Starlette es 1MB, se puede aumentar configurando el servidor
    uvicorn.run("main:app", port=8000, reload=True)
