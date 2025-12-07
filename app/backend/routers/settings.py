from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, UpdateSettings
from app.backend.classes.setting_class import SettingClass
from app.backend.auth.auth_user import get_current_active_user

settings = APIRouter(
    prefix="/settings",
    tags=["Settings"]
)

@settings.put("/update/{id}")
def update(id: int, setting_inputs: UpdateSettings, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    settings_data = setting_inputs.dict(exclude_unset=True)
    result = SettingClass(db).update(id, settings_data)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating settings"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Settings updated successfully",
            "data": None
        }
    )

@settings.get("/edit/{id}")
def edit(id: int, db: Session = Depends(get_db)):
    result = SettingClass(db).get(id)

    if isinstance(result, dict) and result.get("error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Settings retrieved successfully",
            "data": result
        }
    )

@settings.get("/get_token")
def get_token(db: Session = Depends(get_db)):
    result = SettingClass(db).get_simplefactura_token()

    if isinstance(result, dict) and result.get("error"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("error", "Error getting token"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Token retrieved successfully",
            "data": {"token": result}
        }
    )

@settings.get("/validate_token")
def validate_token(db: Session = Depends(get_db)):
    result = SettingClass(db).validate_token()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Token validation completed",
            "data": {"valid": result == 1, "result": result}
        }
    )