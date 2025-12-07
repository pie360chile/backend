from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.backend.db.database import get_db
from app.backend.classes.contact_class import ContactClass
from app.backend.schemas import ContactList, StoreContact, UpdateContact
from app.backend.auth.auth_user import get_current_user

contacts = APIRouter(
    prefix="/contacts",
    tags=["Contacts"]
)

@contacts.post("/")
async def get_contacts(
    request: ContactList,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        contact_obj = ContactClass(db)
        result = contact_obj.get_all(
            page=request.page,
            items_per_page=request.per_page,
            names=request.names,
            subject_type_id=request.subject_type_id,
            schedule_type_id=request.schedule_type_id
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@contacts.get("/edit/{id}")
async def get_contact_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        contact_obj = ContactClass(db)
        result = contact_obj.get(id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result.get("message"))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@contacts.post("/store")
async def store_contact(
    request: StoreContact,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        contact_data = {
            "subject_type_id": request.subject_type_id,
            "schedule_type_id": request.schedule_type_id,
            "names": request.names,
            "lastnames": request.lastnames,
            "email": request.email,
            "celphone": request.celphone,
            "message": request.message
        }
        
        contact_obj = ContactClass(db)
        result = contact_obj.store(contact_data)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@contacts.put("/update/{id}")
async def update_contact(
    id: int,
    request: UpdateContact,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        contact_data = {}
        
        if request.subject_type_id is not None:
            contact_data["subject_type_id"] = request.subject_type_id
        
        if request.schedule_type_id is not None:
            contact_data["schedule_type_id"] = request.schedule_type_id
        
        if request.names is not None:
            contact_data["names"] = request.names
        
        if request.lastnames is not None:
            contact_data["lastnames"] = request.lastnames
        
        if request.email is not None:
            contact_data["email"] = request.email
        
        if request.celphone is not None:
            contact_data["celphone"] = request.celphone
        
        if request.message is not None:
            contact_data["message"] = request.message
        
        contact_obj = ContactClass(db)
        result = contact_obj.update(id, contact_data)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@contacts.delete("/{id}")
async def delete_contact(
    id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        contact_obj = ContactClass(db)
        result = contact_obj.delete(id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result.get("message"))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
