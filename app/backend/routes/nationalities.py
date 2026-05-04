from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, NationalityList, StoreNationality, UpdateNationality
from app.backend.classes.nationalities_class import NationalitiesClass
from app.backend.classes.inspection_api_client import InspectionApiClient
from app.backend.auth.auth_user import get_current_active_user

nationalities = APIRouter(
    prefix="/nationalities",
    tags=["Nationalities"]
)

@nationalities.post("/")
def index(nationality: NationalityList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if nationality.page is None else nationality.page
    result = NationalitiesClass(db).get_all(page=page_value, items_per_page=nationality.per_page, nationality=nationality.nationality)

    if isinstance(result, dict) and result.get("status") == "error":
        error_message = result.get("message", "Error")
        lower_message = error_message.lower() if isinstance(error_message, str) else ""

        if "no data" in lower_message or "no se encontraron datos" in lower_message:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": 200,
                    "message": error_message,
                    "data": []
                }
            )

        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": error_message,
                "data": None
            }
        )

    message = "Complete nationalities list retrieved successfully" if nationality.page is None else "Nationalities retrieved successfully"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@nationalities.post("/store")
def store(nationality: StoreNationality, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    nationality_inputs = nationality.dict()
    result = NationalitiesClass(db).store(nationality_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating nationality"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Nationality created successfully",
            "data": result
        }
    )

@nationalities.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = NationalitiesClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Nationality not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Nationality retrieved successfully",
            "data": result
        }
    )

@nationalities.put("/update/{id}")
def update(id: int, nationality: UpdateNationality, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    nationality_inputs = nationality.dict(exclude_unset=True)
    result = NationalitiesClass(db).update(id, nationality_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating nationality"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Nationality updated successfully",
            "data": result
        }
    )

@nationalities.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = NationalitiesClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Nationality not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Nationality deleted successfully",
            "data": result
        }
    )

@nationalities.post("/import_from_inspection")
def import_from_inspection(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Importa catálogo desde Inspection GET listado/nacionalidades (Bearer). Catálogo global, sin colegio."""
    client = InspectionApiClient()
    if not client.is_configured():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": 503,
                "message": "Inspection API not configured (INSPECTION_API_USERNAME / INSPECTION_API_PASSWORD)",
                "data": None,
            },
        )

    remote = client.fetch_nationalities_list()
    if not remote.get("ok"):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "status": 502,
                "message": remote.get("message") or "Error al obtener nacionalidades desde Inspection",
                "data": remote,
            },
        )

    result = NationalitiesClass(db).import_from_inspection(remote)
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error al importar nacionalidades"),
                "data": None,
            },
        )

    imported = result.get("imported", 0)
    skipped = result.get("skipped", 0)
    msg = f"Importación de nacionalidades finalizada: {imported} nuevas, {skipped} omitidas (duplicadas o sin datos)."
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": msg,
            "data": result,
        },
    )


@nationalities.get("/list")
def list_all(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = NationalitiesClass(db).get_all(page=0, items_per_page=None)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error retrieving nationalities"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Nationalities list retrieved successfully",
            "data": result
        }
    )

