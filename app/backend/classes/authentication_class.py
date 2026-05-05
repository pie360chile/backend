from app.backend.db.models import UserModel, CustomerModel, UsersRolModel
from fastapi import HTTPException
from app.backend.auth.auth_user import pwd_context
from datetime import datetime, timedelta, date
from typing import Union
import os
from jose import jwt, JWTError
import bcrypt
from argon2 import PasswordHasher
from sqlalchemy import func, or_

argon2_hasher = PasswordHasher()

class AuthenticationClass:
    def __init__(self, db):
        self.db = db
    
    def _normalize_rut(self, raw: str) -> str:
        return (raw or "").replace(".", "").replace("-", "").strip().upper()

    def authenticate_user(self, username_or_rut, password):
        username = (username_or_rut or "").strip()
        rut_norm = self._normalize_rut(username)
        user = (
            self.db.query(UserModel)
            .filter(
                or_(
                    func.lower(UserModel.email) == username.lower(),
                    func.upper(
                        func.replace(func.replace(UserModel.rut, ".", ""), "-", "")
                    )
                    == rut_norm,
                ),
                or_(UserModel.deleted_status_id == 0, UserModel.deleted_status_id.is_(None)),
            )
            .first()
        )

        if not user:
            raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

        if not self.verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

        # Verificar licencia del customer, excepto si el usuario tiene rol superadmin (1) entre sus roles activos.
        customer_id = user.customer_id
        has_superadmin_role = (
            self.db.query(UsersRolModel.id)
            .filter(
                UsersRolModel.user_id == user.id,
                UsersRolModel.rol_id == 1,
                or_(UsersRolModel.deleted_status_id == 0, UsersRolModel.deleted_status_id.is_(None)),
            )
            .first()
            is not None
        )
        if customer_id and not has_superadmin_role:
            customer = self.db.query(CustomerModel).filter(CustomerModel.id == customer_id).first()
            if customer and customer.license_time:
                if customer.license_time < date.today():
                    raise HTTPException(status_code=403, detail="La licencia ha expirado. Debe renovarla")

        response_data = {
            "user_data": {
                "id": user.id,
                "rut": user.rut,
                "full_name": user.full_name,
                "customer_id": user.customer_id,
                "email": user.email,
                "phone": user.phone,
                "hashed_password": user.hashed_password,
            }
        }
        return response_data
        
    def verify_password(self, plain_password, hashed_password):
        """
        Verifica una contraseña contra un hash.
        Soporta tanto Argon2 como bcrypt.
        """
        from app.backend.auth.auth_user import verify_password
        return verify_password(plain_password, hashed_password)
    
    def create_token(self, data: dict, time_expire: Union[datetime, None] = None):
        data_copy = data.copy()
        if time_expire is None:
            expires = datetime.utcnow() + timedelta(minutes=1000000)
        else:
            expires = datetime.utcnow() + time_expire

        data_copy.update({"exp": expires})
        token = jwt.encode(data_copy, os.environ['SECRET_KEY'], algorithm=os.environ['ALGORITHM'])

        return token

    def create_password_reset_token(self, user_id: int, minutes: Union[int, None] = None):
        """
        JWT de un solo uso para recuperación de contraseña (claim purpose=password_reset).
        Duración configurable con PASSWORD_RESET_TOKEN_MINUTES (por defecto 60).
        Retorna (token, minutes_used) para alinear el texto del correo con el JWT.
        """
        if minutes is None:
            try:
                minutes = int(os.getenv("PASSWORD_RESET_TOKEN_MINUTES", "60"))
            except ValueError:
                minutes = 60
        minutes_used = max(5, min(minutes, 60 * 24 * 7))  # entre 5 min y 7 días
        payload = {
            "sub": str(user_id),
            "purpose": "password_reset",
        }
        token = self.create_token(payload, timedelta(minutes=minutes_used))
        return token, minutes_used

    def decode_password_reset_token(self, token: str) -> int:
        """Decodifica y valida el JWT de recuperación; devuelve user id."""
        try:
            payload = jwt.decode(
                token,
                os.environ["SECRET_KEY"],
                algorithms=[os.environ["ALGORITHM"]],
            )
        except JWTError:
            raise HTTPException(
                status_code=400,
                detail="El enlace de recuperación no es válido o ha expirado.",
            )
        if payload.get("purpose") != "password_reset":
            raise HTTPException(
                status_code=400,
                detail="El enlace de recuperación no es válido o ha expirado.",
            )
        raw = payload.get("sub")
        try:
            return int(raw)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="El enlace de recuperación no es válido o ha expirado.",
            )

    def update_password(self, user_inputs):
        existing_user = self.db.query(UserModel).filter(UserModel.visual_rut == user_inputs.visual_rut).one_or_none()

        if not existing_user:
            return "No data found"

        existing_user_data = user_inputs.dict(exclude_unset=True)
        for key, value in existing_user_data.items():
            if key == 'hashed_password':
                # Solo hashear si no es ya un hash (no empieza con $2)
                if not (isinstance(value, str) and value.startswith('$2')):
                    value = self.generate_bcrypt_hash(value)
            if hasattr(existing_user, key):
                setattr(existing_user, key, value)

        self.db.commit()

        return 1
        
    def generate_bcrypt_hash(self, input_string):
        """
        Genera un hash de contraseña usando Argon2 (sin límite de 72 bytes).
        Si el input ya es un hash, lo devuelve directamente.
        """
        # Si ya es un hash (empieza con $2 para bcrypt o $argon2 para Argon2), devolverlo directamente
        if isinstance(input_string, str) and (input_string.startswith('$2') or input_string.startswith('$argon2')):
            return input_string
        
        # Usar Argon2 que no tiene límite de 72 bytes
        try:
            hashed_string = argon2_hasher.hash(input_string)
            return hashed_string
        except Exception as e:
            # Fallback a bcrypt si Argon2 falla (para compatibilidad)
            if len(input_string) > 72:
                import hashlib
                sha256_hash = hashlib.sha256(input_string.encode('utf-8')).hexdigest()
                input_string = sha256_hash
            
            encoded_string = input_string.encode('utf-8')
            salt = bcrypt.gensalt()
            hashed_string = bcrypt.hashpw(encoded_string, salt)
            return hashed_string.decode('utf-8')