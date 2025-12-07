from app.backend.db.models import FaqModel
from datetime import datetime

class FaqClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, question=None):
        try:
            query = self.db.query(FaqModel)

            # Filtrar por pregunta si se proporciona
            if question:
                query = query.filter(FaqModel.question.like(f'%{question}%'))

            # Ordenar por ID descendente (más reciente primero)
            query = query.order_by(FaqModel.id.desc())

            # Contar total de registros
            total_items = query.count()

            # Aplicar paginación (page comienza en 1, no en 0)
            if page is None or page < 1:
                page = 1
            offset = (page - 1) * items_per_page
            faqs = query.offset(offset).limit(items_per_page).all()

            if not faqs:
                return {
                    "status": "error",
                    "message": "No data found",
                    "data": None,
                    "total_items": 0,
                    "total_pages": 0,
                    "current_page": page
                }

            # Calcular total de páginas
            total_pages = (total_items + items_per_page - 1) // items_per_page

            # Convertir a diccionarios
            faqs_list = []
            for faq in faqs:
                faq_dict = {
                    "id": faq.id,
                    "question": faq.question,
                    "answer": faq.answer,
                    "added_date": faq.added_date.strftime('%Y-%m-%d %H:%M:%S') if faq.added_date else None,
                    "updated_date": faq.updated_date.strftime('%Y-%m-%d %H:%M:%S') if faq.updated_date else None
                }
                faqs_list.append(faq_dict)

            return {
                "status": "success",
                "data": faqs_list,
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get(self, faq_id):
        try:
            faq = self.db.query(FaqModel).filter(
                FaqModel.id == faq_id
            ).first()

            if not faq:
                return {
                    "status": "error",
                    "message": "FAQ not found"
                }

            faq_dict = {
                "id": faq.id,
                "question": faq.question,
                "answer": faq.answer,
                "added_date": faq.added_date.strftime('%Y-%m-%d %H:%M:%S') if faq.added_date else None,
                "updated_date": faq.updated_date.strftime('%Y-%m-%d %H:%M:%S') if faq.updated_date else None
            }

            return faq_dict

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def store(self, faq_data):
        try:
            new_faq = FaqModel(
                question=faq_data.get('question'),
                answer=faq_data.get('answer'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_faq)
            self.db.commit()
            self.db.refresh(new_faq)

            return {
                "status": "success",
                "message": "FAQ created successfully",
                "data": {
                    "id": new_faq.id
                }
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def update(self, faq_id, faq_data):
        try:
            faq = self.db.query(FaqModel).filter(
                FaqModel.id == faq_id
            ).first()

            if not faq:
                return {
                    "status": "error",
                    "message": "FAQ not found"
                }

            # Actualizar campos
            if faq_data.get('question') is not None:
                faq.question = faq_data.get('question')
            
            if faq_data.get('answer') is not None:
                faq.answer = faq_data.get('answer')

            faq.updated_date = datetime.now()

            self.db.commit()

            return {
                "status": "success",
                "message": "FAQ updated successfully"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def delete(self, faq_id):
        try:
            faq = self.db.query(FaqModel).filter(
                FaqModel.id == faq_id
            ).first()

            if not faq:
                return {
                    "status": "error",
                    "message": "FAQ not found"
                }

            # Hard delete
            self.db.delete(faq)
            self.db.commit()

            return {
                "status": "success",
                "message": "FAQ deleted successfully"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
