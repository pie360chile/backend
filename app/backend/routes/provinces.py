from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user, get_current_superadmin_user
from app.backend.classes.inspection_api_client import InspectionApiClient
from app.backend.classes.province_class import ProvinceClass
from app.backend.db.database import get_db
from app.backend.schemas import ProvinceList, StoreProvince, UpdateProvince, UserLogin

provinces = APIRouter(prefix="/provinces", tags=["Provinces"])


@provinces.post("/")
def index(
    body: ProvinceList,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    page_value = 0 if body.page is None else body.page
    result = ProvinceClass(db).get_all(
        province_name=body.province_name,
        region_id=body.region_id,
        page=page_value,
        items_per_page=body.per_page,
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
            "message": "Provinces retrieved successfully",
            "data": result,
        },
    )


@provinces.post("/store")
def store(
    body: StoreProvince,
    session_user: UserLogin = Depends(get_current_superadmin_user),
    db: Session = Depends(get_db),
):
    result = ProvinceClass(db).store(body.dict(exclude_unset=True))

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating province"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Province created successfully",
            "data": result,
        },
    )


@provinces.get("/edit/{id}")
def edit(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    result = ProvinceClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Province not found"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Province retrieved successfully",
            "data": result,
        },
    )


@provinces.put("/update/{id}")
def update(
    id: int,
    body: UpdateProvince,
    session_user: UserLogin = Depends(get_current_superadmin_user),
    db: Session = Depends(get_db),
):
    result = ProvinceClass(db).update(id, body.dict(exclude_unset=True))

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating province"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Province updated successfully",
            "data": result,
        },
    )


@provinces.delete("/delete/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_superadmin_user),
    db: Session = Depends(get_db),
):
    result = ProvinceClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Province not found"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Province deleted successfully",
            "data": result,
        },
    )


@provinces.post("/import_from_inspection")
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

    remote = client.fetch_provinces_list()
    if not remote.get("ok"):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "status": 502,
                "message": remote.get("message") or "Error al obtener provincias desde Inspection",
                "data": remote,
            },
        )

    result = ProvinceClass(db).import_from_inspection(remote)
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error al importar provincias"),
                "data": None,
            },
        )

    imported = result.get("imported", 0)
    skipped = result.get("skipped", 0)
    msg = f"Importación de provincias finalizada: {imported} nuevas/actualizadas, {skipped} omitidas."
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": msg,
            "data": result,
        },
    )


@provinces.get("/list")
def list_all(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    result = ProvinceClass(db).get_all(page=0, items_per_page=0)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error retrieving provinces"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Provinces list retrieved successfully",
            "data": result,
        },
    )
