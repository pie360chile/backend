from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import Permission, UpdatePermission, UserLogin, PermissionList
from app.backend.classes.permission_class import PermissionClass
from app.backend.classes.user_class import UserClass
from app.backend.auth.auth_user import get_current_active_user
from app.backend.db.models import UserModel
import json

permissions = APIRouter(
    prefix="/permissions",
    tags=["Permissions"]
)

@permissions.post("/")
def index(permission_list: PermissionList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if permission_list.page is None else permission_list.page
    result = PermissionClass(db).get_all(page=page_value, items_per_page=permission_list.per_page, permission=permission_list.permission)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error"),
                "data": None
            }
        )
        
    message = "Complete permissions list retrieved successfully" if permission_list.page is None else "Permissions retrieved successfully"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@permissions.get("/list")
def get_all_list(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    if session_user.rol_id == 1:
        result = PermissionClass(db).get_all_list()
    else:
        result = PermissionClass(db).get_all_list(permission_type_id=2)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error"),
                "data": None
            }
        )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Permissions list retrieved successfully",
            "data": result
        }
    )

@permissions.post("/store")
def store(permission: Permission, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    permission_inputs = permission.dict()
    result = PermissionClass(db).store(permission_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating permission"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Permission created successfully",
            "data": result
        }
    )

@permissions.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = PermissionClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Permission not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Permission retrieved successfully",
            "data": result
        }
    )

@permissions.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = PermissionClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Permission not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Permission deleted successfully",
            "data": result
        }
    )

@permissions.put("/update/{id}")
def update(id: int, permission: UpdatePermission, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    permission_inputs = permission.dict(exclude_unset=True)
    result = PermissionClass(db).update(id, permission_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating permission"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Permission updated successfully",
            "data": result
        }
    )

