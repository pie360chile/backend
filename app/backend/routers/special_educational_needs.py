from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, SpecialEducationalNeedList, StoreSpecialEducationalNeed, UpdateSpecialEducationalNeed
from app.backend.classes.special_educational_need_class import SpecialEducationalNeedClass
from app.backend.auth.auth_user import get_current_active_user

special_educational_needs = APIRouter(
    prefix="/special_educational_needs",
    tags=["Special Educational Needs"]
)

@special_educational_needs.post("/")
def index(need: SpecialEducationalNeedList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if need.page is None else need.page
    result = SpecialEducationalNeedClass(db).get_all(
        page=page_value,
        items_per_page=need.per_page,
        special_educational_needs=need.special_educational_needs
    )

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

    message = "Complete special educational needs list retrieved successfully" if need.page is None else "Special educational needs retrieved successfully"

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@special_educational_needs.post("/store")
def store(need: StoreSpecialEducationalNeed, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    need_inputs = need.dict()
    result = SpecialEducationalNeedClass(db).store(need_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating special educational need"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Special educational need created successfully",
            "data": result
        }
    )

@special_educational_needs.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = SpecialEducationalNeedClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Special educational need not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Special educational need retrieved successfully",
            "data": result
        }
    )

@special_educational_needs.put("/update/{id}")
def update(id: int, need: UpdateSpecialEducationalNeed, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    need_inputs = need.dict(exclude_unset=True)
    result = SpecialEducationalNeedClass(db).update(id, need_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating special educational need"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Special educational need updated successfully",
            "data": result
        }
    )

@special_educational_needs.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = SpecialEducationalNeedClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Special educational need not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Special educational need deleted successfully",
            "data": result
        }
    )

@special_educational_needs.get("/list")
def list_all(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = SpecialEducationalNeedClass(db).get_all(page=0, items_per_page=None)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error retrieving special educational needs"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Special educational needs list retrieved successfully",
            "data": result
        }
    )
