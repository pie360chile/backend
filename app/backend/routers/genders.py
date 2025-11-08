from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, GenderList, StoreGender, UpdateGender
from app.backend.classes.gender_class import GenderClass
from app.backend.auth.auth_user import get_current_active_user

genders = APIRouter(
    prefix="/genders",
    tags=["Genders"]
)

@genders.post("/")
def index(item: GenderList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if item.page is None else item.page
    result = GenderClass(db).get_all(page=page_value, items_per_page=item.per_page, gender=item.gender)

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

    message = "Complete genders list retrieved successfully" if item.page is None else "Genders retrieved successfully"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )
    
@genders.post("/store")
def store(item: StoreGender, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    item_inputs = item.dict()
    result = GenderClass(db).store(item_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating gender"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Gender created successfully",
            "data": result
        }
    )

@genders.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = GenderClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Gender not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Gender retrieved successfully",
            "data": result
        }
    )

@genders.put("/update/{id}")
def update(id: int, item: UpdateGender, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    item_inputs = item.dict(exclude_unset=True)
    result = GenderClass(db).update(id, item_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating gender"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Gender updated successfully",
            "data": result
        }
    )

@genders.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = GenderClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Gender not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Gender deleted successfully",
            "data": result
        }
    )

