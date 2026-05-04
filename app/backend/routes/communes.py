from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user, get_current_superadmin_user
from app.backend.classes.commune_class import CommuneClass
from app.backend.classes.inspection_api_client import InspectionApiClient
from app.backend.db.database import get_db
from app.backend.schemas import CommuneList, StoreCommune, UpdateCommune, UserLogin

communes = APIRouter(prefix="/communes", tags=["Communes"])


@communes.get("/endpoint/list")
def endpoint_list(session_user: UserLogin = Depends(get_current_active_user)):
    """Catálogo remoto de comunas desde Inspection API."""
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

    result = client.fetch_communes_list()
    return JSONResponse(
        status_code=status.HTTP_200_OK if result.get("ok") else status.HTTP_502_BAD_GATEWAY,
        content={
            "status": 200 if result.get("ok") else 502,
            "message": result.get("message", "OK"),
            "data": result,
        },
    )


@communes.post("/")
def index(
    commune: CommuneList,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    page_value = 0 if commune.page is None else commune.page
    result = CommuneClass(db).get_all(
        commune_name=commune.commune_name,
        region_id=commune.region_id,
        page=page_value,
        items_per_page=commune.per_page,
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
            "message": "Communes retrieved successfully",
            "data": result,
        },
    )


@communes.post("/store")
def store(
    commune: StoreCommune,
    session_user: UserLogin = Depends(get_current_superadmin_user),
    db: Session = Depends(get_db),
):
    commune_inputs = commune.dict(exclude_unset=True)
    result = CommuneClass(db).store(commune_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating commune"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Commune created successfully",
            "data": result,
        },
    )


@communes.get("/edit/{id}")
def edit(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    result = CommuneClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Commune not found"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Commune retrieved successfully",
            "data": result,
        },
    )


@communes.put("/update/{id}")
def update(
    id: int,
    commune: UpdateCommune,
    session_user: UserLogin = Depends(get_current_superadmin_user),
    db: Session = Depends(get_db),
):
    commune_inputs = commune.dict(exclude_unset=True)
    result = CommuneClass(db).update(id, commune_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating commune"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Commune updated successfully",
            "data": result,
        },
    )


@communes.delete("/delete/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_superadmin_user),
    db: Session = Depends(get_db),
):
    result = CommuneClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Commune not found"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Commune deleted successfully",
            "data": result,
        },
    )


@communes.post("/import_from_inspection")
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

    remote = client.fetch_communes_list()
    if not remote.get("ok"):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "status": 502,
                "message": remote.get("message") or "Error al obtener comunas desde Inspection",
                "data": remote,
            },
        )

    result = CommuneClass(db).import_from_inspection(remote)
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error al importar comunas"),
                "data": None,
            },
        )

    imported = result.get("imported", 0)
    skipped = result.get("skipped", 0)
    msg = f"Importación de comunas finalizada: {imported} nuevas/actualizadas, {skipped} omitidas."
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": msg,
            "data": result,
        },
    )


@communes.get("/list")
def list_all(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    result = CommuneClass(db).get_all(page=0, items_per_page=0)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error retrieving communes"),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Communes list retrieved successfully",
            "data": result,
        },
    )
