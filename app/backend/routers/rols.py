from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import Rol, UpdateRol, UserLogin
from app.backend.classes.rol_class import RolClass
from app.backend.auth.auth_user import get_current_active_user

rols = APIRouter(
    prefix="/rols",
    tags=["Rols"]
)

@rols.get("/")
def index(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = RolClass(db).get_all()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Roles retrieved successfully",
            "data": result if not isinstance(result, str) else None
        }
    )

@rols.post("/store")
def store(rol:Rol, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    bank_inputs = rol.dict()
    result = RolClass(db).store(bank_inputs)

    if isinstance(result, str) and result.startswith("Error"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result,
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Role created successfully",
            "data": {"id": result}
        }
    )

@rols.get("/edit/{id}")
def edit(id:int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = RolClass(db).get("id", id)

    if not result or isinstance(result, str):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": "Role not found",
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Role retrieved successfully",
            "data": {"id": result.id, "rol": result.rol}
        }
    )

@rols.delete("/delete/{id}")
def delete(id:int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = RolClass(db).delete(id)

    if isinstance(result, str) and (result == "No data found" or result.startswith("Error")):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result,
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Role deleted successfully",
            "data": None
        }
    )

@rols.put("/update/{id}")
def update(id: int, rol: UpdateRol, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    rol_inputs = rol.dict(exclude_unset=True)
    result = RolClass(db).update(id, rol_inputs)

    if isinstance(result, str) and (result == "No data found" or result.startswith("Error")):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result,
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Role updated successfully",
            "data": None
        }
    )