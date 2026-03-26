from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, CommuneList, StoreCommune, UpdateCommune
from app.backend.classes.commune_class import CommuneClass
from app.backend.classes.inspection_api_client import InspectionApiClient
from app.backend.auth.auth_user import get_current_active_user

communes = APIRouter(
    prefix="/communes",
    tags=["Communes"]
)


@communes.get("/endpoint/list")
def endpoint_list(session_user: UserLogin = Depends(get_current_active_user)):
    """
    Catálogo remoto de comunas desde Inspection API (/listado/comunas).
    """
    client = InspectionApiClient()
    if not client.is_configured():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": 503,
                "message": "Inspection API not configured (INSPECTION_API_USERNAME / INSPECTION_API_PASSWORD)",
                "data": None,
            }
        )

    result = client.fetch_communes_list()
    return JSONResponse(
        status_code=status.HTTP_200_OK if result.get("ok") else status.HTTP_502_BAD_GATEWAY,
        content={
            "status": 200 if result.get("ok") else 502,
            "message": result.get("message", "OK"),
            "data": result,
        }
    )

@communes.post("/")
def index(commune: CommuneList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = CommuneClass(db).get_all(commune_name=commune.commune_name, region_id=commune.region_id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error"),
                "data": None
            }
        )
        
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Communes retrieved successfully",
            "data": result
        }
    )

@communes.post("/store")
def store(commune: StoreCommune, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    commune_inputs = commune.dict()
    result = CommuneClass(db).store(commune_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating commune"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Commune created successfully",
            "data": result
        }
    )

@communes.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = CommuneClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Commune not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Commune retrieved successfully",
            "data": result
        }
    )

@communes.put("/update/{id}")
def update(id: int, commune: UpdateCommune, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    commune_inputs = commune.dict(exclude_unset=True)
    result = CommuneClass(db).update(id, commune_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating commune"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Commune updated successfully",
            "data": result
        }
    )

@communes.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = CommuneClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Commune not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Commune deleted successfully",
            "data": result
        }
    )
