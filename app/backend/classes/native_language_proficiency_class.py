from datetime import datetime
from app.backend.db.models import NativeLanguageProficiencyModel

class NativeLanguageProficiencyClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, native_language_proficiency=None):
        try:
            query = self.db.query(
                NativeLanguageProficiencyModel.id,
                NativeLanguageProficiencyModel.native_language_proficiency,
                NativeLanguageProficiencyModel.added_date,
                NativeLanguageProficiencyModel.updated_date
            )

            # Aplicar filtro de búsqueda si se proporciona native_language_proficiency
            if native_language_proficiency and native_language_proficiency.strip():
                query = query.filter(NativeLanguageProficiencyModel.native_language_proficiency.like(f"%{native_language_proficiency.strip()}%"))

            query = query.order_by(NativeLanguageProficiencyModel.id)
            data = query.all()

            serialized_data = [{
                "id": nlp.id,
                "native_language_proficiency": nlp.native_language_proficiency,
                "added_date": nlp.added_date.strftime("%Y-%m-%d %H:%M:%S") if nlp.added_date else None,
                "updated_date": nlp.updated_date.strftime("%Y-%m-%d %H:%M:%S") if nlp.updated_date else None
            } for nlp in data]

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(
                NativeLanguageProficiencyModel.id,
                NativeLanguageProficiencyModel.native_language_proficiency,
                NativeLanguageProficiencyModel.added_date,
                NativeLanguageProficiencyModel.updated_date
            ).filter(NativeLanguageProficiencyModel.id == id).first()

            if data_query:
                nlp_data = {
                    "id": data_query.id,
                    "native_language_proficiency": data_query.native_language_proficiency,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"native_language_proficiency_data": nlp_data}

            else:
                return {"error": "No se encontraron datos para la proficiency especificada."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, nlp_inputs):
        try:
            new_nlp = NativeLanguageProficiencyModel(
                native_language_proficiency=nlp_inputs['native_language_proficiency'],
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_nlp)
            self.db.commit()
            self.db.refresh(new_nlp)

            return {
                "status": "success",
                "message": "Native language proficiency created successfully",
                "native_language_proficiency_id": new_nlp.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(NativeLanguageProficiencyModel).filter(NativeLanguageProficiencyModel.id == id).first()
            if data:
                self.db.delete(data)
                self.db.commit()
                return {"status": "success", "message": "Native language proficiency deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, nlp_inputs):
        try:
            existing_nlp = self.db.query(NativeLanguageProficiencyModel).filter(NativeLanguageProficiencyModel.id == id).one_or_none()

            if not existing_nlp:
                return {"status": "error", "message": "No data found"}

            for key, value in nlp_inputs.items():
                setattr(existing_nlp, key, value)

            existing_nlp.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_nlp)

            return {"status": "success", "message": "Native language proficiency updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
