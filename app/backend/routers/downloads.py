from fastapi import APIRouter, Body, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.classes.download_class import DownloadClass
from app.backend.schemas import DownloadList, StoreDownload, UpdateDownload

downloads = APIRouter(
    prefix="/downloads",
    tags=["Downloads"]
)

# Listado de descargas
@downloads.post("/")
async def get_downloads(
    download_list: DownloadList = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Obtener descargas
        download_class = DownloadClass(db)
        downloads_data = download_class.get_all(
            page=download_list.page,
            items_per_page=download_list.per_page,
            title=download_list.title,
            download_type_id=download_list.download_type_id
        )

        return downloads_data

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Obtener una descarga
@downloads.get("/edit/{download_id}")
async def get_download(
    download_id: int,
    db: Session = Depends(get_db)
):
    try:
        # Obtener descarga
        download_class = DownloadClass(db)
        download = download_class.get(download_id)

        return download

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Crear descarga
@downloads.post("/store")
async def store_download(
    store_download: StoreDownload = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Crear descarga
        download_class = DownloadClass(db)
        download_data = {
            "download_type_id": store_download.download_type_id,
            "title": store_download.title,
            "description": store_download.description,
            "url": store_download.url,
            "tag": store_download.tag,
            "quantity": store_download.quantity
        }

        result = download_class.store(download_data)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Actualizar descarga
@downloads.put("/update/{download_id}")
async def update_download(
    download_id: int,
    update_download: UpdateDownload = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Actualizar descarga
        download_class = DownloadClass(db)
        download_data = {}

        if update_download.download_type_id is not None:
            download_data["download_type_id"] = update_download.download_type_id
        if update_download.title is not None:
            download_data["title"] = update_download.title
        if update_download.description is not None:
            download_data["description"] = update_download.description
        if update_download.url is not None:
            download_data["url"] = update_download.url
        if update_download.tag is not None:
            download_data["tag"] = update_download.tag
        if update_download.quantity is not None:
            download_data["quantity"] = update_download.quantity

        result = download_class.update(download_id, download_data)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Eliminar descarga
@downloads.delete("/{download_id}")
async def delete_download(
    download_id: int,
    db: Session = Depends(get_db)
):
    try:
        # Eliminar descarga
        download_class = DownloadClass(db)
        result = download_class.delete(download_id)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
