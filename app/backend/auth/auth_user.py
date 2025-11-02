from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from fastapi import HTTPException, Depends
from app.backend.db.models import UserModel
import os
from jose import jwt, JWTError
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
import bcrypt

oauth2_scheme = OAuth2PasswordBearer("/login_users/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
    return user
    
def get_current_active_user(current_user: UserModel = Depends(get_current_user)):
    return current_user

def get_user(rut):
    db: Session = next(get_db())

    user = db.query(UserModel). \
                    filter(UserModel.id == rut). \
                    first()
    
    if not user:
        return ""
    return user

def generate_bcrypt_hash(input_string):
    encoded_string = input_string.encode('utf-8')

    salt = bcrypt.gensalt()

    hashed_string = bcrypt.hashpw(encoded_string, salt)

    return hashed_string