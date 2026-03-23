from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, NativeLanguageProficiencyList, StoreNativeLanguageProficiency, UpdateNativeLanguageProficiency
from app.backend.classes.native_language_proficiency_class import NativeLanguageProficiencyClass
from app.backend.auth.auth_user import get_current_active_user

native_language_proficiencies = APIRouter(
    prefix="/native_language_proficiencies",
    tags=["Native Language Proficiencies"]
)

@native_language_proficiencies.post("/")
def index(nlp: NativeLanguageProficiencyList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = NativeLanguageProficiencyClass(db).get_all(native_language_proficiency=nlp.native_language_proficiency)

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
            "message": "Native language proficiencies retrieved successfully",
            "data": result
        }
    )

@native_language_proficiencies.post("/store")
def store(nlp: StoreNativeLanguageProficiency, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    nlp_inputs = nlp.dict()
    result = NativeLanguageProficiencyClass(db).store(nlp_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating native language proficiency"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Native language proficiency created successfully",
            "data": result
        }
    )

@native_language_proficiencies.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = NativeLanguageProficiencyClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Native language proficiency not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Native language proficiency retrieved successfully",
            "data": result
        }
    )

@native_language_proficiencies.put("/update/{id}")
def update(id: int, nlp: UpdateNativeLanguageProficiency, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    nlp_inputs = nlp.dict(exclude_unset=True)
    result = NativeLanguageProficiencyClass(db).update(id, nlp_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating native language proficiency"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Native language proficiency updated successfully",
            "data": result
        }
    )

@native_language_proficiencies.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = NativeLanguageProficiencyClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Native language proficiency not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Native language proficiency deleted successfully",
            "data": result
        }
    )
