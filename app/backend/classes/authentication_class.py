from app.backend.db.models import UserModel, CustomerModel
from fastapi import HTTPException
from app.backend.auth.auth_user import pwd_context
from app.backend.classes.user_class import UserClass
from datetime import datetime, timedelta, date
from typing import Union
import os
from jose import jwt
import json
import bcrypt
from argon2 import PasswordHasher

argon2_hasher = PasswordHasher()

class AuthenticationClass:
    def __init__(self, db):
        self.db = db
    
    def authenticate_user(self, email, password):
        user = UserClass(self.db).get('email', email)

        if not user or user == "No se encontraron datos para el campo especificado." or user.startswith("Error:"):
            raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

        response_data = json.loads(user)

        if not self.verify_password(password, response_data["user_data"]["hashed_password"]):
            raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
        
        # Verificar licencia del customer si el usuario tiene customer_id (excepto rol_id 1)
        rol_id = response_data["user_data"].get("rol_id")
        customer_id = response_data["user_data"].get("customer_id")
        if customer_id and rol_id != 1:
            customer = self.db.query(CustomerModel).filter(CustomerModel.id == customer_id).first()
            if customer and customer.license_time:
                if customer.license_time < date.today():
                    raise HTTPException(status_code=403, detail="La licencia ha expirado. Debe renovarla")
        
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