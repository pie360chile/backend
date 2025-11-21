from fastapi import APIRouter, Depends, status, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, NewsList, StoreNews, UpdateNews
from app.backend.classes.news_class import NewsClass
from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.files_class import FileClass
from typing import Optional
from datetime import datetime
import uuid

news = APIRouter(
    prefix="/news",
    tags=["News"]
)

@news.post("/")
def index(news_item: NewsList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if news_item.page is None else news_item.page
    result = NewsClass(db).get_all(page=page_value, items_per_page=news_item.per_page, title=news_item.title)

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

    message = "Complete news list retrieved successfully" if news_item.page is None else "News retrieved successfully"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@news.post("/store")
async def store(
    news_item: StoreNews = Depends(StoreNews.as_form),
    image: Optional[UploadFile] = File(None),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    news_inputs = news_item.dict()
    file_service = FileClass(db)

    if image is not None and image.filename:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        unique_id = uuid.uuid4().hex[:8]
        file_extension = image.filename.split('.')[-1] if '.' in image.filename else ''
        unique_filename = f"{timestamp}_{unique_id}.{file_extension}" if file_extension else f"{timestamp}_{unique_id}"
        remote_path = f"system/news/{unique_filename}"

        file_service.upload(image, remote_path)
        news_inputs["image"] = file_service.get(remote_path)

    result = NewsClass(db).store(news_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating news"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "News created successfully",
            "data": result
        }
    )

@news.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = NewsClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "News not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "News retrieved successfully",
            "data": result
        }
    )

@news.put("/update/{id}")
async def update(
    id: int,
    news_item: UpdateNews = Depends(UpdateNews.as_form),
    image: Optional[UploadFile] = File(None),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    news_inputs = news_item.dict()
    file_service = FileClass(db)

    # Procesar imagen si se proporciona
    if image is not None and image.filename:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        unique_id = uuid.uuid4().hex[:8]
        file_extension = image.filename.split('.')[-1] if '.' in image.filename else ''
        unique_filename = f"{timestamp}_{unique_id}.{file_extension}" if file_extension else f"{timestamp}_{unique_id}"
        remote_path = f"system/news/{unique_filename}"

        file_service.upload(image, remote_path)
        news_inputs["image"] = file_service.get(remote_path)

    result = NewsClass(db).update(id, news_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating news"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "News updated successfully",
            "data": result
        }
    )

@news.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    news_service = NewsClass(db)
    file_service = FileClass(db)

    existing = news_service.get(id)

    if isinstance(existing, dict) and existing.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": existing.get("message", "News not found"),
                "data": None
            }
        )

    if isinstance(existing, dict) and existing.get("error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": existing.get("error"),
                "data": None
            }
        )

    image_url = None
    if isinstance(existing, dict) and existing.get("news_data"):
        image_url = existing["news_data"].get("image")

    result = news_service.delete(id)
 
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "News not found"),
                "data": None
            }
        )

    if image_url:
        remote_path = file_service.extract_remote_path(image_url)
        if remote_path:
            try:
                file_service.delete(remote_path)
            except HTTPException:
                pass
 
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "News deleted successfully",
            "data": result
        }
    )

