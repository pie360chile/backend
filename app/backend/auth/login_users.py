from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.classes.authentication_class import AuthenticationClass
from app.backend.schemas import ForgotPassword, UpdatePassWord
from datetime import timedelta
from app.backend.classes.dropbox_class import DropboxClass

login_users = APIRouter(
    prefix="/login_users",
    tags=["LoginUser"]
)

@login_users.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = AuthenticationClass(db).authenticate_user(form_data.username, form_data.password)
    access_token_expires = timedelta(minutes=30)
    access_token_jwt = AuthenticationClass(db).create_token({'sub': str(user.rut)}, access_token_expires)
    signature = DropboxClass(db).get('/signatures/', str(user.signature))
    return {
        "access_token": access_token_jwt, 
        "rut": user.rut,
        "status_id": user.status_id,
        "visual_rut": user.visual_rut,
        "rol_id": user.rol_id,
        "nickname": user.nickname,
        "names": user.names,
        "father_lastname": user.father_lastname,
        "mother_lastname": user.mother_lastname,
        "entrance_company": user.entrance_company,
        "job_position": user.job_position,
        "signature": signature,
        "signature_type_id": user.signature_type_id,
        "full_name": user.names +' '+ user.father_lastname +' '+ user.mother_lastname,
        "token_type": "bearer"
    }

@login_users.post("/logout")
def logout(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = AuthenticationClass(db).authenticate_user(form_data.username, form_data.password)
    access_token_expires = timedelta(minutes=30)
    access_token_jwt = AuthenticationClass(db).create_token({'sub': str(user.rut)}, access_token_expires)

    return {
        "access_token": access_token_jwt, 
        "rut": user.rut,
        "visual_rut": user.visual_rut,
        "rol_id": user.rol_id,
        "nickname": user.nickname,
        "token_type": "bearer"
    }

@login_users.post("/forgot")
def forgot(employee_inputs: ForgotPassword, db: Session = Depends(get_db)):

    data = AuthenticationClass(db).forgot(employee_inputs)

    return {
        "message": data
    }

@login_users.patch("/update_password")
def update_password(user_inputs: UpdatePassWord, db: Session = Depends(get_db)):

    data = AuthenticationClass(db).update_password(user_inputs)

    return {
        "message": data
    }
