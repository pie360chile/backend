from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import BankDescriptionList, StoreBankDescription, UpdateBankDescription, UserLogin
from app.backend.classes.bank_description_class import BankDescriptionClass
from app.backend.auth.auth_user import get_current_active_user

bank_descriptions = APIRouter(
    prefix="/bank_descriptions",
    tags=["Bank Descriptions"]
)

@bank_descriptions.post("/")
def index(bank_description_list: BankDescriptionList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Si page es None, usar 0 para obtener todos sin paginación
    page = bank_description_list.page if bank_description_list.page is not None else 0
    per_page = bank_description_list.per_page if bank_description_list.per_page else 10
    result = BankDescriptionClass(db).get_all(
        school_id=bank_description_list.school_id,
        document_id=bank_description_list.document_id,
        question_number=bank_description_list.question_number,
        page=page,
        items_per_page=per_page
    )

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
            "message": "Bank descriptions retrieved successfully",
            "data": result
        }
    )

@bank_descriptions.post("/store")
def store(bank_description: StoreBankDescription, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    bank_description_inputs = bank_description.dict()
    result = BankDescriptionClass(db).store(bank_description_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating bank description"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Bank description created successfully",
            "data": {"id": result.get("id")}
        }
    )

@bank_descriptions.get("/{id}")
def get(id: int, school_id: int, document_id: int, question_number: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = BankDescriptionClass(db).get(id, school_id, document_id, question_number)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Bank description not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Bank description retrieved successfully",
            "data": result
        }
    )

@bank_descriptions.put("/{id}")
def update(id: int, bank_description: UpdateBankDescription, school_id: int, document_id: int, question_number: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    bank_description_inputs = bank_description.dict(exclude_unset=True)
    result = BankDescriptionClass(db).update(id, bank_description_inputs, school_id, document_id, question_number)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error updating bank description"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Bank description updated successfully",
            "data": {"id": result.get("id")}
        }
    )

@bank_descriptions.delete("/{id}")
def delete(id: int, school_id: int, document_id: int, question_number: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = BankDescriptionClass(db).delete(id, school_id, document_id, question_number)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error deleting bank description"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Bank description deleted successfully",
            "data": None
        }
    )
