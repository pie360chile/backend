from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from fastapi import HTTPException, Depends
from app.backend.db.models import UserModel
import os
from jose import jwt, JWTError
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
import bcrypt
from argon2 import PasswordHasher

oauth2_scheme = OAuth2PasswordBearer("/login_users/token")
# Usar solo Argon2 para evitar problemas de compatibilidad con bcrypt 5.0.0
# Argon2 no tiene límite de 72 bytes y es más seguro
argon2_hasher = PasswordHasher()

# Función helper para verificar contraseñas (soporta Argon2 y bcrypt)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica una contraseña contra un hash.
    Soporta tanto Argon2 como bcrypt.
    """
    # Si es un hash de Argon2, usar argon2_hasher directamente
    if isinstance(hashed_password, str) and hashed_password.startswith('$argon2'):
        try:
            argon2_hasher.verify(hashed_password, plain_password)
            return True
        except Exception:
            return False
    # Para bcrypt, usar passlib solo si es necesario (puede fallar con bcrypt 5.0.0)
    elif isinstance(hashed_password, str) and hashed_password.startswith('$2'):
        try:
            # Intentar con passlib primero
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            # Si falla, intentar con bcrypt directamente
            try:
                import bcrypt
                return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
            except Exception:
                return False
    return False

# Mantener pwd_context para compatibilidad (pero usar verify_password en su lugar)
try:
    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
except Exception:
    pwd_context = None

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        decoded_token = jwt.decode(token, os.environ['SECRET_KEY'], algorithms=[os.environ['ALGORITHM']])

        username = decoded_token.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

    user = get_user(username)

    if user is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    
    # Sobrescribir con los datos del token que pueden haber cambiado (como school_id al seleccionar escuela)
    if 'rol_id' in decoded_token:
        user.rol_id = decoded_token['rol_id']
    if 'customer_id' in decoded_token:
        user.customer_id = decoded_token['customer_id']
    if 'school_id' in decoded_token:
        user.school_id = decoded_token['school_id']
    if 'teaching_id' in decoded_token:
        user.teaching_id = decoded_token['teaching_id']
    if 'course_id' in decoded_token:
        user.course_id = decoded_token['course_id']
    if 'career_type_id' in decoded_token:
        user.career_type_id = decoded_token['career_type_id']

    return user
    
def get_current_active_user(current_user: UserModel = Depends(get_current_user)):
    return current_user

def get_user(rut):
    db: Session = next(get_db())

    user = db.query(UserModel). \
                    filter(UserModel.rut == rut). \
                    filter(UserModel.deleted_status_id == 0). \
                    first()
    
    if not user:
        return ""
    return user

def generate_bcrypt_hash(input_string):
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