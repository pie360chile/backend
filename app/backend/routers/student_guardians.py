from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, StudentGuardianList, StoreStudentGuardian, UpdateStudentGuardian
from app.backend.classes.student_guardian_class import StudentGuardianClass
from app.backend.auth.auth_user import get_current_active_user

student_guardians = APIRouter(
    prefix="/student_guardians",
    tags=["Student Guardians"]
)

@student_guardians.post("/")
def index(guardian: StudentGuardianList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if guardian.page is None else guardian.page
    result = StudentGuardianClass(db).get_all(
        page=page_value,
        items_per_page=guardian.per_page,
        student_id=guardian.student_id,
        names=guardian.names
    )

    if isinstance(result, dict) and result.get("status") == "error":
        error_message = result.get("message", "Error")
        lower_message = error_message.lower() if isinstance(error_message, str) else ""

        if "no data" in lower_message or "no se encontraron datos" in lower_message:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": 200,
                    "message": error_message,
                    "data": []
                }
            )

        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": error_message,
                "data": None
            }
        )

    message = "Complete guardians list retrieved successfully" if guardian.page is None else "Guardians retrieved successfully"

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@student_guardians.post("/store")
def store(guardian: StoreStudentGuardian, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    guardian_inputs = guardian.dict()
    result = StudentGuardianClass(db).store(guardian_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating guardian"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Guardian created successfully",
            "data": result
        }
    )

@student_guardians.get("/edit/{student_id}")
def edit(student_id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = StudentGuardianClass(db).get(student_id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Guardian not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Guardian retrieved successfully",
            "data": result
        }
    )

@student_guardians.put("/update/{id}")
def update(id: int, guardian: UpdateStudentGuardian, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    guardian_inputs = guardian.dict(exclude_unset=True)
    result = StudentGuardianClass(db).update(id, guardian_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating guardian"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Guardian updated successfully",
            "data": result
        }
    )

@student_guardians.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = StudentGuardianClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Guardian not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Guardian deleted successfully",
            "data": result
        }
    )

@student_guardians.get("/list")
def list_all(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = StudentGuardianClass(db).get_all(page=0, items_per_page=None)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error retrieving guardians"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Guardians list retrieved successfully",
            "data": result
        }
    )
