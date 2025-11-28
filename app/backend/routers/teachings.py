from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, TeachingList, StoreTeaching, UpdateTeaching
from app.backend.classes.teaching_class import TeachingClass
from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.school_class import SchoolClass

teachings = APIRouter(
    prefix="/teachings",
    tags=["Teachings"]
)

@teachings.post("/")
def index(teaching: TeachingList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Obtener school_id de la sesión del usuario
    school_id = session_user.school_id if session_user else None
    
    # Si no hay school_id, devolver array vacío
    if school_id is None:
        message = "Complete teachings list retrieved successfully" if teaching.page is None else "Teachings retrieved successfully"
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": message,
                "data": [] if teaching.page is None else {
                    "total_items": 0,
                    "total_pages": 0,
                    "current_page": teaching.page if teaching.page else 1,
                    "items_per_page": teaching.per_page,
                    "data": []
                }
            }
        )
    
    page_value = 0 if teaching.page is None else teaching.page
    result = TeachingClass(db).get_all(page=page_value, items_per_page=teaching.per_page, teaching_name=teaching.teaching_name, school_id=school_id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error"),
                "data": None
            }
        )

    message = "Complete teachings list retrieved successfully" if teaching.page is None else "Teachings retrieved successfully"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@teachings.get("/list")
def get_all_list(school_id: int = None, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Si no viene school_id por parámetro, obtenerlo de la sesión del usuario
    if school_id is None:
        school_id = session_user.school_id if session_user else None
    
    # Si no hay school_id, devolver array vacío
    if school_id is None:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Teachings list retrieved successfully",
                "data": []
            }
        )
    
    result = TeachingClass(db).get_all_list(school_id=school_id)

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
            "message": "Teachings list retrieved successfully",
            "data": result
        }
    )

@teachings.post("/store")
def store(teaching: StoreTeaching, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    teaching_inputs = teaching.dict()
    
    # Obtener school_id de la sesión del usuario
    school_id = session_user.school_id if session_user else None
    
    # Agregar school_id a teaching_inputs
    teaching_inputs['school_id'] = school_id
    
    result = TeachingClass(db).store(teaching_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating teaching"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Teaching created successfully",
            "data": result
        }
    )

@teachings.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = TeachingClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Teaching not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Teaching retrieved successfully",
            "data": result
        }
    )

@teachings.put("/update/{id}")
def update(id: int, teaching: UpdateTeaching, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    teaching_inputs = teaching.dict(exclude_unset=True)
    
    # Obtener school_id de la sesión del usuario
    school_id = session_user.school_id if session_user else None
    
    # Agregar school_id a teaching_inputs
    teaching_inputs['school_id'] = school_id
    
    result = TeachingClass(db).update(id, teaching_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating teaching"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Teaching updated successfully",
            "data": result
        }
    )

@teachings.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = TeachingClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Teaching not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Teaching deleted successfully",
            "data": result
        }
    )