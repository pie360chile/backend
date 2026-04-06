from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.backend.classes.authentication_class import AuthenticationClass
from app.backend.classes.rol_class import RolClass
from app.backend.classes.school_class import SchoolClass
from app.backend.classes.user_class import UserClass
from app.backend.classes.audit_class import AuditClass
from app.backend.classes.email_class import EmailServiceClass
from app.backend.auth.auth_user import get_current_active_user
from app.backend.db.models import (
    ProfessionalModel,
    ProfessionalTeachingCourseModel,
    SchoolModel,
    UserModel,
)
from datetime import datetime, timedelta
from app.backend.schemas import UserLogin
import json
import logging
import os
from urllib.parse import quote
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class ForgotPasswordBody(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)


class ResetPasswordBody(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=256)


authentications = APIRouter(
    prefix="/authentications",
    tags=["Authentications"]
)


@authentications.post("/forgot-password")
def forgot_password(body: ForgotPasswordBody, db: Session = Depends(get_db)):
    """
    Recuperación de contraseña: siempre responde igual (no revela si el correo existe).
    Si el usuario existe y SMTP está configurado, envía correo HTML con enlace JWT.
    """
    email_norm = body.email.strip().lower()
    generic = {
        "status": 200,
        "message": "Si el correo está registrado en Pie360, recibirás instrucciones para restablecer tu contraseña.",
    }

    try:
        user = (
            db.query(UserModel)
            .filter(
                func.lower(UserModel.email) == email_norm,
                UserModel.deleted_status_id == 0,
            )
            .first()
        )
        if user and (user.email or "").strip():
            auth = AuthenticationClass(db)
            token, minutes_used = auth.create_password_reset_token(user.id)
            base = (os.getenv("FRONTEND_PUBLIC_URL") or "http://localhost:5173").rstrip("/")
            reset_url = f"{base}/reset-password?token={quote(token, safe='')}"

            mailer = EmailServiceClass()
            html = mailer.password_reset_email_html(
                reset_url=reset_url,
                user_name=(user.full_name or "").strip() or None,
                expires_minutes=minutes_used,
            )
            sent = mailer.send_html(
                user.email.strip(),
                "Pie360 — Restablecer contraseña",
                html,
                text_plain=f"Restablece tu contraseña abriendo este enlace en el navegador:\n{reset_url}",
            )
            if not sent:
                logger.warning(
                    "forgot-password: usuario encontrado pero no se pudo enviar el correo (SMTP)."
                )
    except Exception:
        logger.exception("forgot-password: error interno (no expuesto al cliente)")

    return JSONResponse(status_code=status.HTTP_200_OK, content=generic)


@authentications.post("/reset-password")
def reset_password(body: ResetPasswordBody, db: Session = Depends(get_db)):
    """Restablece contraseña con el token recibido por correo (JWT purpose=password_reset)."""
    try:
        auth = AuthenticationClass(db)
        user_id = auth.decode_password_reset_token(body.token.strip())
        user = (
            db.query(UserModel)
            .filter(UserModel.id == user_id, UserModel.deleted_status_id == 0)
            .first()
        )
        if not user:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": 400,
                    "message": "No se pudo restablecer la contraseña. Solicita un nuevo enlace.",
                    "data": None,
                },
            )
        user.hashed_password = auth.generate_bcrypt_hash(body.new_password)
        user.updated_date = datetime.utcnow()
        db.commit()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Contraseña actualizada correctamente.",
                "data": None,
            },
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"status": e.status_code, "message": e.detail, "data": None},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error al restablecer la contraseña: {str(e)}",
                "data": None,
            },
        )


@authentications.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        user = AuthenticationClass(db).authenticate_user(form_data.username, form_data.password)
        
        user_rol_id = user["user_data"].get("rol_id")
        
        rol_result = RolClass(db).get(user_rol_id) if user_rol_id else None
        
        # Obtener el nombre del rol y validar que exista
        rol_name = ""
        if isinstance(rol_result, dict):
            if "rol_data" in rol_result:
                rol_name = rol_result["rol_data"].get("rol", "")
            elif "error" in rol_result:
                print("ERROR AL OBTENER ROL:", rol_result["error"])
        
        # Obtener permisos del rol desde rols_permissions
        permissions = rol_result.get("rol_data", {}).get("permissions", []) if isinstance(rol_result, dict) and rol_result.get("rol_data") else []
        
        # Obtener datos del colegio si existe customer_id y el rol NO es 2 (Administrador)
        customer_id = user["user_data"].get("customer_id")
        school_id = user["user_data"].get("school_id")
        school_data = None
        
        # Solo traer school si el rol_id NO es 2 (Administrador seleccionará escuela después)
        if customer_id and user_rol_id != 2:
            schools_list = SchoolClass(db).get_all(page=0, customer_id=customer_id)
            if isinstance(schools_list, list) and len(schools_list) > 0:
                school_data = schools_list[0]
                school_id = school_data.get("id") if school_data else None

        # Obtener professional_teaching_course si el rol no es 1, 2 ni Coordinador
        professional_teaching_course = None
        ptc_teaching_id = None
        ptc_course_id = None
        
        if user_rol_id not in [1, 2] and rol_name.lower() != "coordinador":
            # Buscar el profesional por identification_number
            professional = db.query(ProfessionalModel).filter(
                ProfessionalModel.identification_number == user["user_data"]["rut"]
            ).first()
            
            if professional:
                # Buscar en professionals_teachings_courses
                ptc = db.query(ProfessionalTeachingCourseModel).filter(
                    ProfessionalTeachingCourseModel.professional_id == professional.id,
                    ProfessionalTeachingCourseModel.deleted_status_id == 0
                ).first()
                
                if ptc:
                    ptc_teaching_id = ptc.teaching_id
                    ptc_course_id = ptc.course_id
                    professional_teaching_course = {
                        "id": ptc.id,
                        "professional_id": ptc.professional_id,
                        "teaching_id": ptc.teaching_id,
                        "course_id": ptc.course_id,
                        "added_date": ptc.added_date.strftime("%Y-%m-%d %H:%M:%S") if ptc.added_date else None,
                        "updated_date": ptc.updated_date.strftime("%Y-%m-%d %H:%M:%S") if ptc.updated_date else None
                    }

        token_expires = timedelta(minutes=9999999)
        token_data = {
            'sub': str(user["user_data"]["email"]),
            'rol_id': user_rol_id,
            'customer_id': customer_id,
            'school_id': school_id,
            'teaching_id': ptc_teaching_id,
            'course_id': ptc_course_id
        }
        token = AuthenticationClass(db).create_token(token_data, token_expires)
        expires_in_seconds = token_expires.total_seconds()

        # Guardar registro de auditoría (login)
        try:
            AuditClass(db).store(
                user_id=user["user_data"]["id"],
                rol_id=user_rol_id
            )
        except Exception as audit_error:
            # No fallar el login si hay error en auditoría, solo loguear
            print(f"Error guardando registro de auditoría: {str(audit_error)}")

        data = {
            "access_token": token,
            "user_id": user["user_data"]["id"],
            "rut": user["user_data"]["rut"],
            "rol_id": user_rol_id if user_rol_id is not None else 0,
            "customer_id": customer_id,
            "school_id": school_id,
            "school": school_data,
            "rol": rol_name,
            "permissions": permissions,
            "professional_teaching_course": professional_teaching_course,
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

@authentications.post("/select-school/{school_id}")
def select_school(school_id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    try:
        # Por id de usuario (varias cuentas pueden compartir el mismo RUT)
        user_fresh = UserClass(db).get('id', session_user.id)
        
        if not user_fresh or user_fresh == "No se encontraron datos para el campo especificado." or user_fresh.startswith("Error:"):
            raise HTTPException(status_code=401, detail="User not found")
        
        user_data_fresh = json.loads(user_fresh)["user_data"]
        
        user_rol_id = user_data_fresh.get("rol_id")
        customer_id = user_data_fresh.get("customer_id")
        
        # Obtener datos del rol
        rol_result = RolClass(db).get(user_rol_id) if user_rol_id else None
        rol_name = ""
        permissions = []
        
        if isinstance(rol_result, dict) and "rol_data" in rol_result:
            rol_name = rol_result["rol_data"].get("rol", "")
            permissions = rol_result["rol_data"].get("permissions", [])
        
        # Obtener el school específico por ID
        school_data = db.query(SchoolModel).filter(
            SchoolModel.id == school_id,
            SchoolModel.customer_id == customer_id,
            SchoolModel.deleted_status_id == 0
        ).first()
        
        if not school_data:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": "School not found or does not belong to your customer",
                    "data": None
                }
            )
        
        # Serializar school_data
        school_dict = {
            "id": school_data.id,
            "customer_id": school_data.customer_id,
            "deleted_status_id": school_data.deleted_status_id,
            "school_name": school_data.school_name,
            "school_address": school_data.school_address,
            "director_name": school_data.director_name,
            "community_school_password": school_data.community_school_password,
            "added_date": school_data.added_date.strftime("%Y-%m-%d %H:%M:%S") if school_data.added_date else None,
            "updated_date": school_data.updated_date.strftime("%Y-%m-%d %H:%M:%S") if school_data.updated_date else None
        }
        
        # Obtener professional_teaching_course si el rol no es 1, 2 ni Coordinador
        professional_teaching_course = None
        ptc_teaching_id = None
        ptc_course_id = None
        
        if user_rol_id not in [1, 2] and rol_name.lower() != "coordinador":
            # Buscar el profesional por identification_number
            professional = db.query(ProfessionalModel).filter(
                ProfessionalModel.identification_number == user_data_fresh["rut"]
            ).first()
            
            if professional:
                # Buscar en professionals_teachings_courses
                ptc = db.query(ProfessionalTeachingCourseModel).filter(
                    ProfessionalTeachingCourseModel.professional_id == professional.id,
                    ProfessionalTeachingCourseModel.deleted_status_id == 0
                ).first()
                
                if ptc:
                    ptc_teaching_id = ptc.teaching_id
                    ptc_course_id = ptc.course_id
                    professional_teaching_course = {
                        "id": ptc.id,
                        "professional_id": ptc.professional_id,
                        "teaching_id": ptc.teaching_id,
                        "course_id": ptc.course_id,
                        "added_date": ptc.added_date.strftime("%Y-%m-%d %H:%M:%S") if ptc.added_date else None,
                        "updated_date": ptc.updated_date.strftime("%Y-%m-%d %H:%M:%S") if ptc.updated_date else None
                    }

        # Generar nuevo token con el mismo tiempo de expiración e incluir school_id
        token_expires = timedelta(minutes=9999999)
        token_data = {
            'sub': str(user_data_fresh["email"]),
            'rol_id': user_rol_id,
            'customer_id': customer_id,
            'school_id': school_id,
            'teaching_id': ptc_teaching_id,
            'course_id': ptc_course_id
        }
        token = AuthenticationClass(db).create_token(token_data, token_expires)
        expires_in_seconds = token_expires.total_seconds()
        
        data = {
            "access_token": token,
            "user_id": user_data_fresh["id"],
            "rut": user_data_fresh["rut"],
            "rol_id": user_rol_id if user_rol_id is not None else 0,
            "customer_id": customer_id,
            "school_id": school_id,
            "school": school_dict,
            "rol": rol_name,
            "permissions": permissions,
            "professional_teaching_course": professional_teaching_course,
            "full_name": user_data_fresh["full_name"],
            "email": user_data_fresh["email"],
            "token_type": "bearer",
            "expires_in": expires_in_seconds
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "School selected successfully",
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
        ud = user["user_data"]
        access_token_jwt = AuthenticationClass(db).create_token({'sub': str(ud["email"])}, access_token_expires)

        data = {
            "access_token": access_token_jwt,
            "rut": ud.get("rut"),
            "rol_id": ud.get("rol_id"),
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
