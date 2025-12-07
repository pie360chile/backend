from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.backend.db.database import get_db
from app.backend.classes.document_type_class import DocumentTypeClass
from app.backend.schemas import UserLogin, DocumentTypeList, StoreDocumentType, UpdateDocumentType
from app.backend.auth.auth_user import get_current_active_user

document_types = APIRouter(
    prefix="/document_types",
    tags=["Document Types"]
)

@document_types.post("/")
def index(
    doc_list: DocumentTypeList,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    doc_type_class = DocumentTypeClass(db=db)

    page = doc_list.page if doc_list.page and doc_list.page > 0 else 0
    per_page = doc_list.per_page
    document = doc_list.document

    result = doc_type_class.get_all(page=page, items_per_page=per_page, document=document)

    if isinstance(result, dict) and result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message")
        )

    return {
        "status": 200,
        "message": "success",
        "data": result
    }

@document_types.get("/list")
def get_list(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    doc_type_class = DocumentTypeClass(db=db)

    result = doc_type_class.get_all(page=0, items_per_page=0, document=None)

    if isinstance(result, dict) and result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message")
        )

    return {
        "status": 200,
        "message": "success",
        "data": result
    }

@document_types.post("/store")
def store(
    doc_data: StoreDocumentType,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    doc_type_class = DocumentTypeClass(db=db)

    doc_inputs = doc_data.dict()

    result = doc_type_class.store(doc_inputs)

    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message")
        )

    return {
        "status": 200,
        "message": result.get("message"),
        "data": result
    }

@document_types.get("/edit/{id}")
def edit(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    doc_type_class = DocumentTypeClass(db=db)

    result = doc_type_class.get(id=id)

    if isinstance(result, dict) and result.get("status") == "error":
        return {
            "status": 200,
            "message": result.get("message"),
            "data": None
        }

    return {
        "status": 200,
        "message": "success",
        "data": result
    }

@document_types.put("/update/{id}")
def update(
    id: int,
    doc_data: UpdateDocumentType,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    doc_type_class = DocumentTypeClass(db=db)

    doc_inputs = doc_data.dict(exclude_unset=True)

    result = doc_type_class.update(id=id, doc_inputs=doc_inputs)

    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message")
        )

    return {
        "status": 200,
        "message": result.get("message"),
        "data": result
    }

@document_types.delete("/delete/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    doc_type_class = DocumentTypeClass(db=db)

    result = doc_type_class.delete(id=id)

    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message")
        )

    return {
        "status": 200,
        "message": result.get("message"),
        "data": result
    }
