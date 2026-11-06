from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.web_page_class import WebPageClass
from app.backend.db.database import get_db
from app.backend.schemas import UserLogin

web_pages = APIRouter(
    prefix="/web-pages",
    tags=["Web Pages"],
)


class UpdateWebPageBody(BaseModel):
    title: Optional[str] = None
    menu_label: Optional[str] = None
    sort_order: Optional[int] = None
    is_published: Optional[int] = Field(default=None, description="1=publicado, 0=borrador")
    content: Optional[Dict[str, Any]] = None


@web_pages.get("/")
def list_web_pages(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Listado admin (todas las páginas)."""
    data = WebPageClass(db).get_all(published_only=False)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "OK", "data": data},
    )


@web_pages.get("/public")
def list_public_web_pages(db: Session = Depends(get_db)):
    """Listado público (solo publicadas)."""
    data = WebPageClass(db).get_all(published_only=True)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "OK", "data": data},
    )


@web_pages.get("/public/{slug}")
def get_public_web_page(slug: str, db: Session = Depends(get_db)):
    data = WebPageClass(db).get_by_slug(slug, published_only=True)
    if not data:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status": 404, "message": "Página no encontrada", "data": None},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "OK", "data": data},
    )


@web_pages.get("/edit/{page_id}")
def get_web_page(
    page_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = WebPageClass(db).get_by_id(page_id)
    if not data:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status": 404, "message": "Página no encontrada", "data": None},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "OK", "data": data},
    )


@web_pages.put("/update/{page_id}")
def update_web_page(
    page_id: int,
    body: UpdateWebPageBody,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    result = WebPageClass(db).update(page_id, body.model_dump(exclude_unset=True))
    if result.get("status") == "error":
        code = (
            status.HTTP_404_NOT_FOUND
            if "no encontrada" in (result.get("message") or "").lower()
            else status.HTTP_400_BAD_REQUEST
        )
        return JSONResponse(
            status_code=code,
            content={"status": code, "message": result.get("message"), "data": None},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": result.get("message", "OK"),
            "data": result.get("data"),
        },
    )
