from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import Rol, UpdateRol, UserLogin, RolList
from app.backend.classes.rol_class import RolClass
from app.backend.db.models import UserModel
from app.backend.auth.auth_user import get_current_active_user

rols = APIRouter(
    prefix="/rols",
    tags=["Rols"]
)

@rols.post("/")
def index(rol_list: RolList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Obtener customer_id y school_id del usuario en sesión
    customer_id = session_user.customer_id if session_user else None
    
    page_value = 0 if rol_list.page is None else rol_list.page
    result = RolClass(db).get_all(page=page_value, items_per_page=rol_list.per_page, rol=rol_list.rol, customer_id=customer_id)
        
    message = "Complete rols list retrieved successfully" if rol_list.page is None else "Rols retrieved successfully"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@rols.get("/list")
def get_all_list(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Obtener customer_id y school_id del usuario en sesión
    customer_id = session_user.customer_id if session_user else None
    school_id = session_user.school_id if session_user else None
    
    result = RolClass(db).get_all(page=0, customer_id=customer_id, school_id=school_id)
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Complete rols list retrieved successfully",
            "data": result
        }
    )

@rols.post("/store")
def store(rol: Rol, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Obtener customer_id y school_id del usuario en sesión
    customer_id = session_user.customer_id if session_user else None
    school_id = session_user.school_id if session_user else None
    
    rol_inputs = rol.dict()
    rol_inputs['customer_id'] = customer_id
    rol_inputs['school_id'] = school_id
    rol_inputs['deleted_status_id'] = 0
    
    result = RolClass(db).store(rol_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating Rol"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Rol created successfully",
            "data": result
        }
    )

@rols.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    try:
        rol_class = RolClass(db)
        result = rol_class.get(id)

        if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("error") or result.get("message", "Rol not found"),
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Rol retrieved successfully",
                "data": result
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error: {str(e)}",
                "data": None
            }
        )

@rols.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = RolClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Rol not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Rol deleted successfully",
            "data": result
        }
    )

@rols.put("/update/{id}")
def update(id: int, rol: UpdateRol, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Obtener school_id del usuario en sesión
    school_id = session_user.school_id if session_user else None
    
    rol_inputs = rol.dict(exclude_unset=True)
    rol_inputs['school_id'] = school_id
    result = RolClass(db).update(id, rol_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating Rol"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Rol updated successfully",
            "data": result
        }
    )