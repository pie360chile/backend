from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, NewsList, StoreNews, UpdateNews
from app.backend.classes.news_class import NewsClass
from app.backend.auth.auth_user import get_current_active_user

news = APIRouter(
    prefix="/news",
    tags=["News"]
)

@news.post("/")
def index(news_item: NewsList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if news_item.page is None else news_item.page
    result = NewsClass(db).get_all(page=page_value, items_per_page=news_item.per_page, title=news_item.title)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error"),
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
def store(news_item: StoreNews, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    news_inputs = news_item.dict()
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
def update(id: int, news_item: UpdateNews, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    news_inputs = news_item.dict(exclude_unset=True)
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
    result = NewsClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "News not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "News deleted successfully",
            "data": result
        }
    )

