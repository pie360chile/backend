from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.classes.authentication_class import AuthenticationClass
from app.backend.classes.rol_class import RolClass
from app.backend.classes.school_class import SchoolClass
from datetime import timedelta
from app.backend.schemas import UserLogin
import json

authentications = APIRouter(
    prefix="/authentications",
    tags=["Authentications"]
)

@authentications.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        user = AuthenticationClass(db).authenticate_user(form_data.username, form_data.password)
        
        # Debug: imprimir el usuario completo
        print("USER DATA:", user["user_data"])
        
        user_rol_id = user["user_data"].get("rol_id")
        
        print("ROL_ID:", user_rol_id)
        
        rol_result = RolClass(db).get(user_rol_id) if user_rol_id else None
        
        print("ROL_RESULT:", rol_result)
        
        # Obtener el nombre del rol y validar que exista
        rol_name = ""
        if isinstance(rol_result, dict):
            if "rol_data" in rol_result:
                rol_name = rol_result["rol_data"].get("rol", "")
            elif "error" in rol_result:
                print("ERROR AL OBTENER ROL:", rol_result["error"])
        
        print("ROL_NAME:", rol_name)
        
        # Obtener permisos del rol desde rols_permissions
        permissions = rol_result.get("rol_data", {}).get("permissions", []) if isinstance(rol_result, dict) and rol_result.get("rol_data") else []
        
        print("PERMISSIONS:", permissions)
        
        token_expires = timedelta(minutes=9999999)
        token = AuthenticationClass(db).create_token({'sub': str(user["user_data"]["rut"])}, token_expires)
        expires_in_seconds = token_expires.total_seconds()

        # Obtener datos del colegio si existe customer_id
        customer_id = user["user_data"].get("customer_id")
        school_data = None
        
        if customer_id:
            schools_list = SchoolClass(db).get_all(page=0, customer_id=customer_id)
            if isinstance(schools_list, list) and len(schools_list) > 0:
                school_data = schools_list[0]

        data = {
            "access_token": token,
            "user_id": user["user_data"]["id"],
            "rut": user["user_data"]["rut"],
            "rol_id": user_rol_id if user_rol_id is not None else 0,
            "customer_id": customer_id,
            "school": school_data,
            "rol": rol_name,
            "permissions": permissions,
            "full_name": user["user_data"]["full_name"],
            "email": user["user_data"]["email"],
            "token_type": "bearer",
            "expires_in": expires_in_seconds
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Login successful",
                "data": data
            }
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "status": e.status_code,
                "message": e.detail,
                "data": None
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Internal server error: {str(e)}",
                "data": None
            }
        )

@authentications.post("/logout")
def logout(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        user = AuthenticationClass(db).authenticate_user(form_data.username, form_data.password)
        access_token_expires = timedelta(minutes=9999999)
        access_token_jwt = AuthenticationClass(db).create_token({'sub': str(user.rut)}, access_token_expires)

        data = {
            "access_token": access_token_jwt, 
            "rut": user.rut,
            "visual_rut": user.visual_rut,
            "rol_id": user.rol_id,
            "nickname": user.nickname,
            "token_type": "bearer"
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Logout successful",
                "data": data
            }
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "status": e.status_code,
                "message": e.detail,
                "data": None
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Internal server error: {str(e)}",
                "data": None
            }
        )