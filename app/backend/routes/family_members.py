from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, FamilyMemberList, StoreFamilyMember, UpdateFamilyMember
from app.backend.classes.family_members_class import FamilyMembersClass
from app.backend.auth.auth_user import get_current_active_user

family_members = APIRouter(
    prefix="/family_members",
    tags=["Family Members"]
)

@family_members.post("/")
def index(member: FamilyMemberList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if member.page is None else member.page
    result = FamilyMembersClass(db).get_all(page=page_value, items_per_page=member.per_page, family_member=member.family_member)

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

    message = "Complete family members list retrieved successfully" if member.page is None else "Family members retrieved successfully"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@family_members.post("/store")
def store(member: StoreFamilyMember, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    member_inputs = member.dict()
    result = FamilyMembersClass(db).store(member_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating family member"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Family member created successfully",
            "data": result
        }
    )

@family_members.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = FamilyMembersClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Family member not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Family member retrieved successfully",
            "data": result
        }
    )

@family_members.put("/update/{id}")
def update(id: int, member: UpdateFamilyMember, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    member_inputs = member.dict(exclude_unset=True)
    result = FamilyMembersClass(db).update(id, member_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating family member"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Family member updated successfully",
            "data": result
        }
    )

@family_members.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = FamilyMembersClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Family member not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Family member deleted successfully",
            "data": result
        }
    )

@family_members.get("/list")
def list(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = FamilyMembersClass(db).get_all(page=0, items_per_page=None)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error retrieving family members"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Family members list retrieved successfully",
            "data": result
        }
    )

