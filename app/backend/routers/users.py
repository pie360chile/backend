from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import User, UpdateUser, UserLogin, RecoverUser, ConfirmEmail, UserList
from app.backend.classes.user_class import UserClass
from app.backend.auth.auth_user import get_current_active_user
import json

users = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@users.post("/")
def index(user: UserList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = UserClass(db).get_all(user.rut, user.page)

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
            "message": "Users retrieved successfully",
            "data": result
        }
    )

@users.post("/store")
def store(user:User, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    user_inputs = user.dict()
    result = UserClass(db).store(user_inputs)

    if result == 0:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": "Error creating user",
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "User created successfully",
            "data": {"id": result}
        }
    )

@users.get("/refresh_password/{rut}")
def resfresh_password(rut:int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = UserClass(db).refresh_password(rut)

    if result == 0:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": "Error refreshing password",
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Password refreshed successfully",
            "data": None
        }
    )

@users.get("/edit/{id}")
def edit(id:int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = UserClass(db).get('id', id)
    
    if not result or result == "No se encontraron datos para el campo especificado." or result.startswith("Error:"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": "User not found",
                "data": None
            }
        )

    try:
        user_data = json.loads(result) if isinstance(result, str) else result
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "User retrieved successfully",
                "data": user_data
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error processing user data: {str(e)}",
                "data": None
            }
        )

@users.delete("/delete/{id}")
def delete(id:int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = UserClass(db).delete(id)

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
            "message": "User deleted successfully",
            "data": None
        }
    )

@users.put("/update/{id}")
def update(id: int, user: UpdateUser, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    user_inputs = user.dict(exclude_unset=True)
    result = UserClass(db).update(id, user_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": 400,
                "message": result.get("message", "Error updating user"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "User updated successfully",
            "data": None
        }
    )

@users.post("/recover")
def recover(user:RecoverUser, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    user_inputs = user.dict()
    result = UserClass(db).recover(user_inputs)

    if result == 0:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": "Error recovering user",
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "User recovered successfully",
            "data": None
        }
    )

@users.patch("/confirm_email")
def confirm_email(user_inputs:ConfirmEmail, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = UserClass(db).confirm_email(user_inputs)

    if result == 0:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": "Error confirming email",
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Email confirmed successfully",
            "data": None
        }
    )