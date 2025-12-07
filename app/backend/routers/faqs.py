from fastapi import APIRouter, Body, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.classes.faq_class import FaqClass
from app.backend.schemas import FaqList, StoreFaq, UpdateFaq

faqs = APIRouter(
    prefix="/faqs",
    tags=["FAQs"]
)

# Listado de FAQs
@faqs.post("/")
async def get_faqs(
    faq_list: FaqList = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Obtener FAQs
        faq_class = FaqClass(db)
        faqs_data = faq_class.get_all(
            page=faq_list.page,
            items_per_page=faq_list.per_page,
            question=faq_list.question
        )

        return faqs_data

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Obtener un FAQ
@faqs.get("/edit/{faq_id}")
async def get_faq(
    faq_id: int,
    db: Session = Depends(get_db)
):
    try:
        # Obtener FAQ
        faq_class = FaqClass(db)
        faq = faq_class.get(faq_id)

        return faq

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Crear FAQ
@faqs.post("/store")
async def store_faq(
    store_faq: StoreFaq = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Crear FAQ
        faq_class = FaqClass(db)
        faq_data = {
            "question": store_faq.question,
            "answer": store_faq.answer
        }

        result = faq_class.store(faq_data)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Actualizar FAQ
@faqs.put("/update/{faq_id}")
async def update_faq(
    faq_id: int,
    update_faq: UpdateFaq = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Actualizar FAQ
        faq_class = FaqClass(db)
        faq_data = {}

        if update_faq.question is not None:
            faq_data["question"] = update_faq.question
        if update_faq.answer is not None:
            faq_data["answer"] = update_faq.answer

        result = faq_class.update(faq_id, faq_data)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Eliminar FAQ
@faqs.delete("/{faq_id}")
async def delete_faq(
    faq_id: int,
    db: Session = Depends(get_db)
):
    try:
        # Eliminar FAQ
        faq_class = FaqClass(db)
        result = faq_class.delete(faq_id)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
