from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, RegionList, StoreRegion, UpdateRegion
from app.backend.classes.region_class import RegionClass
from app.backend.classes.inspection_api_client import InspectionApiClient
from app.backend.auth.auth_user import get_current_active_user

regions = APIRouter(
    prefix="/regions",
    tags=["Regions"]
)


@regions.get("/endpoint/list")
def endpoint_list(session_user: UserLogin = Depends(get_current_active_user)):
    """
    Catálogo remoto de regiones/provincias desde Inspection API (/listado/provincias).
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

    result = client.fetch_regions_list()
    return JSONResponse(
        status_code=status.HTTP_200_OK if result.get("ok") else status.HTTP_502_BAD_GATEWAY,
        content={
            "status": 200 if result.get("ok") else 502,
            "message": result.get("message", "OK"),
            "data": result,
        }
    )

@regions.post("/")
def index(region: RegionList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = RegionClass(db).get_all(region_name=region.region_name)
    print(result)

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
            "message": "Regions retrieved successfully",
            "data": result
        }
    )

@regions.post("/store")
def store(region: StoreRegion, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    region_inputs = region.dict()
    result = RegionClass(db).store(region_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating region"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Region created successfully",
            "data": result
        }
    )

@regions.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = RegionClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Region not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Region retrieved successfully",
            "data": result
        }
    )

@regions.put("/update/{id}")
def update(id: int, region: UpdateRegion, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    region_inputs = region.dict(exclude_unset=True)
    result = RegionClass(db).update(id, region_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating region"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Region updated successfully",
            "data": result
        }
    )

@regions.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = RegionClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Region not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Region deleted successfully",
            "data": result
        }
    )
