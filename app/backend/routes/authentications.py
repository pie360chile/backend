from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.backend.classes.authentication_class import AuthenticationClass
from app.backend.classes.rol_class import RolClass
from app.backend.classes.audit_class import AuditClass
from app.backend.classes.email_class import EmailServiceClass
from app.backend.auth.auth_user import get_current_active_user
from app.backend.db.models import (
    RolModel,
    ProfessionalModel,
    ProfessionalTeachingCourseModel,
    SchoolModel,
    UserModel,
    UsersRolModel,
)
from datetime import datetime, timedelta
from app.backend.schemas import UserLogin
import logging
import os
from urllib.parse import quote
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


def _active_user_roles(db: Session, user_id: int):
    rows = (
        db.query(
            RolModel.id,
            RolModel.rol,
            RolModel.customer_id,
            RolModel.school_id,
        )
        .join(UsersRolModel, UsersRolModel.rol_id == RolModel.id)
        .filter(
            UsersRolModel.user_id == user_id,
            or_(
                UsersRolModel.deleted_status_id == 0,
                UsersRolModel.deleted_status_id.is_(None),
                UsersRolModel.rol_id == 1,  # super admin siempre visible si está relacionado
            ),
            or_(
                RolModel.deleted_status_id == 0,
                RolModel.deleted_status_id.is_(None),
                RolModel.id == 1,  # rol global super admin
            ),
        )
        .order_by(RolModel.id.asc())
        .all()
    )
    return [
        {
            "rol_id": r.id,
            "rol": r.rol,
            "customer_id": r.customer_id,
            "school_id": r.school_id,
        }
        for r in rows
    ]


def _ensure_superadmin_if_admin_equivalent(db: Session, roles: list[dict]):
    role_ids = {int(r.get("rol_id", 0)) for r in roles}
    if 2 in role_ids and 1 not in role_ids:
        superadmin_row = (
            db.query(RolModel)
            .filter(
                RolModel.id == 1,
                or_(RolModel.deleted_status_id == 0, RolModel.deleted_status_id.is_(None)),
            )
            .first()
        )
        if superadmin_row:
            roles.append(
                {
                    "rol_id": int(superadmin_row.id),
                    "rol": superadmin_row.rol or "Super Administrador",
                    "customer_id": superadmin_row.customer_id,
                    "school_id": superadmin_row.school_id,
                }
            )
            roles.sort(key=lambda x: int(x.get("rol_id", 0)))
    return roles


def _available_schools_for_current_role(db: Session, customer_id: int, rol_id: int, user_id: int):
    base_query = db.query(SchoolModel).filter(
        SchoolModel.customer_id == customer_id,
        SchoolModel.deleted_status_id == 0,
    )
    if rol_id in (0, None):
        return []

    rol_row = (
        db.query(RolModel)
        .filter(
            RolModel.id == rol_id,
            or_(RolModel.deleted_status_id == 0, RolModel.deleted_status_id.is_(None)),
        )
        .first()
    )
    if not rol_row:
        return []

    # Administrador (2): puede entrar a cualquier colegio de su cliente.
    if int(rol_id) == 2:
        rows = base_query.all()
    else:
        # Para otros roles: mostrar colegios donde ESTE usuario tenga asignado ese tipo de rol.
        # Si tiene ese rol en varios colegios, verá varios; si solo en uno, verá uno.
        same_role_school_ids = (
            db.query(RolModel.school_id)
            .join(UsersRolModel, UsersRolModel.rol_id == RolModel.id)
            .filter(
                UsersRolModel.user_id == user_id,
                or_(UsersRolModel.deleted_status_id == 0, UsersRolModel.deleted_status_id.is_(None)),
                RolModel.customer_id == customer_id,
                RolModel.rol == rol_row.rol,
                or_(RolModel.deleted_status_id == 0, RolModel.deleted_status_id.is_(None)),
                RolModel.school_id.isnot(None),
            )
            .distinct()
            .all()
        )
        allowed_ids = [int(x[0]) for x in same_role_school_ids if x and x[0] is not None]

        if allowed_ids:
            rows = base_query.filter(SchoolModel.id.in_(allowed_ids)).all()
        elif rol_row.school_id:
            rows = base_query.filter(SchoolModel.id == rol_row.school_id).all()
        else:
            rows = []

    return [
        {
            "id": s.id,
            "customer_id": s.customer_id,
            "deleted_status_id": s.deleted_status_id,
            "school_name": s.school_name,
            "school_address": s.school_address,
            "director_name": s.director_name,
            "community_school_password": s.community_school_password,
            "added_date": s.added_date.strftime("%Y-%m-%d %H:%M:%S") if s.added_date else None,
            "updated_date": s.updated_date.strftime("%Y-%m-%d %H:%M:%S") if s.updated_date else None,
        }
        for s in rows
    ]


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
        user_data = user["user_data"]
        user_roles = _active_user_roles(db, int(user_data["id"]))
        user_roles = _ensure_superadmin_if_admin_equivalent(db, user_roles)
        if not user_roles:
            raise HTTPException(status_code=403, detail="El usuario no tiene roles asignados")

        # Si tiene múltiples roles, primero debe seleccionar rol (incluyendo Super Administrador si aplica).
        if len(user_roles) > 1:
            token_expires = timedelta(minutes=9999999)
            token = AuthenticationClass(db).create_token(
                {
                    "sub": str(user_data["email"]),
                    "rol_id": 0,
                    "customer_id": user_data.get("customer_id"),
                    "school_id": None,
                },
                token_expires,
            )
            data = {
                "access_token": token,
                "user_id": user_data["id"],
                "rut": user_data["rut"],
                "rol_id": 0,
                "customer_id": user_data.get("customer_id"),
                "school_id": None,
                "school": None,
                "rol": "",
                "permissions": [],
                "professional_teaching_course": None,
                "full_name": user_data["full_name"],
                "email": user_data["email"],
                "token_type": "bearer",
                "expires_in": token_expires.total_seconds(),
                "requires_role_selection": True,
                "available_roles": user_roles,
            }
        else:
            chosen_rol_id = int(user_roles[0]["rol_id"])
            rol_result = RolClass(db).get(chosen_rol_id) if chosen_rol_id else None
            rol_name = ""
            if isinstance(rol_result, dict) and "rol_data" in rol_result:
                rol_name = rol_result["rol_data"].get("rol", "")
            permissions = rol_result.get("rol_data", {}).get("permissions", []) if isinstance(rol_result, dict) and rol_result.get("rol_data") else []

            customer_id = user_data.get("customer_id")
            # Selección de colegio siempre obligatoria después de login/rol.
            school_id = None
            school_data = None

            token_expires = timedelta(minutes=9999999)
            token_data = {
                'sub': str(user_data["email"]),
                'rol_id': chosen_rol_id,
                'customer_id': customer_id,
                'school_id': school_id,
                'teaching_id': None,
                'course_id': None
            }
            token = AuthenticationClass(db).create_token(token_data, token_expires)
            data = {
                "access_token": token,
                "user_id": user_data["id"],
                "rut": user_data["rut"],
                "rol_id": chosen_rol_id,
                "customer_id": customer_id,
                "school_id": school_id,
                "school": school_data,
                "rol": rol_name,
                "permissions": permissions,
                "professional_teaching_course": None,
                "full_name": user_data["full_name"],
                "email": user_data["email"],
                "token_type": "bearer",
                "expires_in": token_expires.total_seconds(),
                "requires_role_selection": False,
            }

        try:
            AuditClass(db).store(
                user_id=user_data["id"],
                rol_id=data.get("rol_id"),
            )
        except Exception as audit_error:
            print(f"Error guardando registro de auditoría: {str(audit_error)}")

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


@authentications.post("/select-role/{rol_id}")
def select_role(rol_id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    try:
        user_row = (
            db.query(UserModel)
            .filter(UserModel.id == session_user.id)
            .filter(or_(UserModel.deleted_status_id == 0, UserModel.deleted_status_id.is_(None)))
            .first()
        )
        if not user_row:
            raise HTTPException(status_code=401, detail="User not found")

        rel = (
            db.query(UsersRolModel.id)
            .filter(
                UsersRolModel.user_id == user_row.id,
                UsersRolModel.rol_id == rol_id,
                or_(
                    UsersRolModel.deleted_status_id == 0,
                    UsersRolModel.deleted_status_id.is_(None),
                    UsersRolModel.rol_id == 1,  # permitir super admin global
                ),
            )
            .first()
        )
        if not rel:
            # Equivalencia solicitada: Administrador (2) puede elegir Super Administrador (1).
            if int(rol_id) == 1:
                admin_rel = (
                    db.query(UsersRolModel.id)
                    .filter(
                        UsersRolModel.user_id == user_row.id,
                        UsersRolModel.rol_id == 2,
                        or_(UsersRolModel.deleted_status_id == 0, UsersRolModel.deleted_status_id.is_(None)),
                    )
                    .first()
                )
                if not admin_rel:
                    raise HTTPException(status_code=404, detail="Rol no asignado a este usuario")
            else:
                raise HTTPException(status_code=404, detail="Rol no asignado a este usuario")

        rol_result = RolClass(db).get(rol_id)
        rol_name = ""
        permissions = []
        if isinstance(rol_result, dict) and "rol_data" in rol_result:
            rol_name = rol_result["rol_data"].get("rol", "")
            permissions = rol_result["rol_data"].get("permissions", [])

        # Selección de colegio siempre obligatoria después de seleccionar rol.
        school_id = None
        school_data = None

        token_expires = timedelta(minutes=9999999)
        token = AuthenticationClass(db).create_token(
            {
                "sub": str(user_row.email),
                "rol_id": int(rol_id),
                "customer_id": user_row.customer_id,
                "school_id": school_id,
                "teaching_id": None,
                "course_id": None,
            },
            token_expires,
        )
        data = {
            "access_token": token,
            "user_id": user_row.id,
            "rut": user_row.rut,
            "rol_id": int(rol_id),
            "customer_id": user_row.customer_id,
            "school_id": school_id,
            "school": school_data,
            "rol": rol_name,
            "permissions": permissions,
            "professional_teaching_course": None,
            "full_name": user_row.full_name,
            "email": user_row.email,
            "token_type": "bearer",
            "expires_in": token_expires.total_seconds(),
            "requires_role_selection": False,
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "Role selected successfully", "data": data},
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"status": e.status_code, "message": e.detail, "data": None},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": f"Internal server error: {str(e)}", "data": None},
        )

@authentications.post("/select-school/{school_id}")
def select_school(school_id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    try:
        user_row = (
            db.query(UserModel)
            .filter(UserModel.id == session_user.id)
            .filter(or_(UserModel.deleted_status_id == 0, UserModel.deleted_status_id.is_(None)))
            .first()
        )
        if not user_row:
            raise HTTPException(status_code=401, detail="User not found")

        user_rol_id = int(getattr(session_user, "rol_id", 0) or 0)
        customer_id = user_row.customer_id
        
        # Obtener datos del rol
        rol_result = RolClass(db).get(user_rol_id) if user_rol_id else None
        rol_name = ""
        permissions = []
        
        if isinstance(rol_result, dict) and "rol_data" in rol_result:
            rol_name = rol_result["rol_data"].get("rol", "")
            permissions = rol_result["rol_data"].get("permissions", [])
        
        allowed_schools = _available_schools_for_current_role(db, customer_id, user_rol_id, int(user_row.id))
        school_data = next((s for s in allowed_schools if int(s["id"]) == int(school_id)), None)
        
        if not school_data:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": "School not found or does not belong to your customer",
                    "data": None
                }
            )
        
        school_dict = school_data
        
        # Obtener professional_teaching_course si el rol no es 1, 2 ni Coordinador
        professional_teaching_course = None
        ptc_teaching_id = None
        ptc_course_id = None
        
        if user_rol_id not in [1, 2] and rol_name.lower() != "coordinador":
            # Buscar el profesional por identification_number
            professional = db.query(ProfessionalModel).filter(
                ProfessionalModel.identification_number == user_row.rut
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
            'sub': str(user_row.email),
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
            "user_id": user_row.id,
            "rut": user_row.rut,
            "rol_id": user_rol_id if user_rol_id is not None else 0,
            "customer_id": customer_id,
            "school_id": school_id,
            "school": school_dict,
            "rol": rol_name,
            "permissions": permissions,
            "professional_teaching_course": professional_teaching_course,
            "full_name": user_row.full_name,
            "email": user_row.email,
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


@authentications.get("/available-schools")
def available_schools(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    try:
        customer_id = int(getattr(session_user, "customer_id", 0) or 0)
        user_rol_id = int(getattr(session_user, "rol_id", 0) or 0)
        if customer_id <= 0 or user_rol_id <= 0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": 400, "message": "Rol o cliente inválido para seleccionar colegio", "data": []},
            )

        data = _available_schools_for_current_role(db, customer_id, user_rol_id, int(session_user.id))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": data},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": f"Internal server error: {str(e)}", "data": []},
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
