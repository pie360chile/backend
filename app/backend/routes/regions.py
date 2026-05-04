from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user, get_current_superadmin_user
from app.backend.classes.inspection_api_client import InspectionApiClient
from app.backend.classes.region_class import RegionClass
from app.backend.db.database import get_db
from app.backend.schemas import RegionList, StoreRegion, UpdateRegion, UserLogin

regions = APIRouter(prefix="/regions", tags=["Regions"])


@regions.get("/endpoint/list")
def endpoint_list(session_user: UserLogin = Depends(get_current_active_user)):
    """
    Catálogo remoto de provincias desde Inspection API (compat: mismo payload que `fetch_provinces_list`).
    """
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

    result = client.fetch_regions_list()
    return JSONResponse(
        status_code=status.HTTP_200_OK if result.get("ok") else status.HTTP_502_BAD_GATEWAY,
        content={
            "status": 200 if result.get("ok") else 502,
            "message": result.get("message", "OK"),
            "data": result,
        },
    )


@regions.post("/")
def index(
    region: RegionList,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    page_value = 0 if region.page is None else region.page
    result = RegionClass(db).get_all(
        region_name=region.region_name,
        page=page_value,
        items_per_page=region.per_page,
    )

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Regions retrieved successfully",
            "data": result,
        },
    )


@regions.post("/store")
def store(
    region: StoreRegion,
    session_user: UserLogin = Depends(get_current_superadmin_user),
    db: Session = Depends(get_db),
):
    region_inputs = region.dict(exclude_unset=True)
    result = RegionClass(db).store(region_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating region"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Region created successfully",
            "data": result,
        },
    )


@regions.get("/edit/{id}")
def edit(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    result = RegionClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Region not found"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Region retrieved successfully",
            "data": result,
        },
    )


@regions.put("/update/{id}")
def update(
    id: int,
    region: UpdateRegion,
    session_user: UserLogin = Depends(get_current_superadmin_user),
    db: Session = Depends(get_db),
):
    region_inputs = region.dict(exclude_unset=True)
    result = RegionClass(db).update(id, region_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating region"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Region updated successfully",
            "data": result,
        },
    )


@regions.delete("/delete/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_superadmin_user),
    db: Session = Depends(get_db),
):
    result = RegionClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Region not found"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Region deleted successfully",
            "data": result,
        },
    )


@regions.post("/import_from_inspection")
def import_from_inspection(
    session_user: UserLogin = Depends(get_current_superadmin_user),
    db: Session = Depends(get_db),
):
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

    remote = client.fetch_regiones_list()
    if not remote.get("ok"):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "status": 502,
                "message": remote.get("message") or "Error al obtener regiones desde Inspection",
                "data": remote,
            },
        )

    result = RegionClass(db).import_from_inspection(remote)
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error al importar regiones"),
                "data": None,
            },
        )

    imported = result.get("imported", 0)
    skipped = result.get("skipped", 0)
    msg = f"Importación de regiones finalizada: {imported} nuevas/actualizadas, {skipped} omitidas."
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": msg,
            "data": result,
        },
    )


@regions.get("/list")
def list_all(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    result = RegionClass(db).get_all(page=0, items_per_page=0)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error retrieving regions"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Regions list retrieved successfully",
            "data": result,
        },
    )
