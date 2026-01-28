from app.backend.db.models import BankDescriptionModel
from datetime import datetime

class BankDescriptionClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, school_id, document_id, question_number, page=0, items_per_page=10):
        try:
            query = self.db.query(BankDescriptionModel).filter(
                BankDescriptionModel.school_id == school_id,
                BankDescriptionModel.document_id == document_id,
                BankDescriptionModel.question_number == question_number
            ).order_by(BankDescriptionModel.id.desc())

            # Si page es None, 0 o no se proporciona, devolver todos sin paginación
            if not page or page == 0:
                data = query.all()
                serialized_data = [{
                    "id": item.id,
                    "school_id": item.school_id,
                    "document_id": item.document_id,
                    "question_number": item.question_number,
                    "bank_description": item.bank_description,
                    "added_date": item.added_date.isoformat() if item.added_date else None,
                    "updated_date": item.updated_date.isoformat() if item.updated_date else None
                } for item in data]

                return serialized_data
            else:
                # Paginación activa
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1

                if page < 1:
                    return {"status": "error", "message": "Invalid page number"}
                
                if total_items > 0 and page > total_pages:
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {"status": "error", "message": "No data found"}

                serialized_data = [{
                    "id": item.id,
                    "school_id": item.school_id,
                    "document_id": item.document_id,
                    "question_number": item.question_number,
                    "bank_description": item.bank_description,
                    "added_date": item.added_date.isoformat() if item.added_date else None,
                    "updated_date": item.updated_date.isoformat() if item.updated_date else None
                } for item in data]

                return {
                    "data": serialized_data,
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page
                }

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get(self, id, school_id, document_id, question_number):
        try:
            data_query = self.db.query(BankDescriptionModel).filter(
                BankDescriptionModel.id == id,
                BankDescriptionModel.school_id == school_id,
                BankDescriptionModel.document_id == document_id,
                BankDescriptionModel.question_number == question_number
            ).first()

            if not data_query:
                return {"status": "error", "message": "Bank description not found"}

            return {
                "id": data_query.id,
                "school_id": data_query.school_id,
                "document_id": data_query.document_id,
                "question_number": data_query.question_number,
                "bank_description": data_query.bank_description,
                "added_date": data_query.added_date.isoformat() if data_query.added_date else None,
                "updated_date": data_query.updated_date.isoformat() if data_query.updated_date else None
            }

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def store(self, bank_description_inputs):
        try:
            new_bank_description = BankDescriptionModel(
                school_id=bank_description_inputs.get('school_id'),
                document_id=bank_description_inputs.get('document_id'),
                question_number=bank_description_inputs.get('question_number'),
                bank_description=bank_description_inputs.get('bank_description'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_bank_description)
            self.db.commit()
            self.db.refresh(new_bank_description)

            return {
                "status": "success",
                "message": "Bank description created successfully",
                "id": new_bank_description.id
            }

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, bank_description_inputs, school_id, document_id, question_number):
        try:
            bank_description = self.db.query(BankDescriptionModel).filter(
                BankDescriptionModel.id == id,
                BankDescriptionModel.school_id == school_id,
                BankDescriptionModel.document_id == document_id,
                BankDescriptionModel.question_number == question_number
            ).first()

            if not bank_description:
                return {"status": "error", "message": "Bank description not found"}

            if 'bank_description' in bank_description_inputs and bank_description_inputs['bank_description'] is not None:
                bank_description.bank_description = bank_description_inputs['bank_description']
            
            bank_description.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(bank_description)

            return {
                "status": "success",
                "message": "Bank description updated successfully",
                "id": bank_description.id
            }

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def delete(self, id, school_id, document_id, question_number):
        try:
            bank_description = self.db.query(BankDescriptionModel).filter(
                BankDescriptionModel.id == id,
                BankDescriptionModel.school_id == school_id,
                BankDescriptionModel.document_id == document_id,
                BankDescriptionModel.question_number == question_number
            ).first()

            if not bank_description:
                return {"status": "error", "message": "Bank description not found"}

            self.db.delete(bank_description)
            self.db.commit()

            return {"status": "success", "message": "Bank description deleted successfully"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}
