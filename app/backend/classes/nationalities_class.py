from datetime import datetime
from app.backend.db.models import NationalityModel

class NationalitiesClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, nationality=None):
        try:
            query = self.db.query(
                NationalityModel.id,
                NationalityModel.nationality,
                NationalityModel.added_date,
                NationalityModel.updated_date
            ).filter(NationalityModel.deleted_status_id == 0)

            # Aplicar filtro de búsqueda si se proporciona nationality
            if nationality and nationality.strip():
                query = query.filter(NationalityModel.nationality.like(f"%{nationality.strip()}%"))

            query = query.order_by(NationalityModel.id)

            if page > 0:
                if page < 1:
                    page = 1

                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page if items_per_page else 0

                if total_items == 0 or total_pages == 0 or page > total_pages:
                    return {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                serialized_data = [{
                    "id": nat.id,
                    "nationality": nat.nationality,
                    "added_date": nat.added_date.strftime("%Y-%m-%d %H:%M:%S") if nat.added_date else None,
                    "updated_date": nat.updated_date.strftime("%Y-%m-%d %H:%M:%S") if nat.updated_date else None
                } for nat in data]

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }

            else:
                data = query.all()

                serialized_data = [{
                    "id": nat.id,
                    "nationality": nat.nationality,
                    "added_date": nat.added_date.strftime("%Y-%m-%d %H:%M:%S") if nat.added_date else None,
                    "updated_date": nat.updated_date.strftime("%Y-%m-%d %H:%M:%S") if nat.updated_date else None
                } for nat in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_all_list(self):
        """Retorna todas las nationalities sin paginación ni búsqueda"""
        try:
            query = self.db.query(
                NationalityModel.id,
                NationalityModel.nationality,
                NationalityModel.added_date,
                NationalityModel.updated_date
            ).filter(NationalityModel.deleted_status_id == 0).order_by(NationalityModel.id)
            
            data = query.all()

            serialized_data = [{
                "id": nat.id,
                "nationality": nat.nationality,
                "added_date": nat.added_date.strftime("%Y-%m-%d %H:%M:%S") if nat.added_date else None,
                "updated_date": nat.updated_date.strftime("%Y-%m-%d %H:%M:%S") if nat.updated_date else None
            } for nat in data]

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(NationalityModel).filter(NationalityModel.id == id).first()

            if data_query:
                nationality_data = {
                    "id": data_query.id,
                    "nationality": data_query.nationality,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"nationality_data": nationality_data}

            else:
                return {"error": "No se encontraron datos para la nationality especificada."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, nationality_inputs):
        try:
            new_nationality = NationalityModel(
                nationality=nationality_inputs['nationality'],
                deleted_status_id=0,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_nationality)
            self.db.commit()
            self.db.refresh(new_nationality)

            return {
                "status": "success",
                "message": "Nationality created successfully",
                "nationality_id": new_nationality.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(NationalityModel).filter(NationalityModel.id == id).first()
            if data:
                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Nationality deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, nationality_inputs):
        try:
            existing_nationality = self.db.query(NationalityModel).filter(NationalityModel.id == id).one_or_none()

            if not existing_nationality:
                return {"status": "error", "message": "No data found"}

            for key, value in nationality_inputs.items():
                setattr(existing_nationality, key, value)

            existing_nationality.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_nationality)

            return {"status": "success", "message": "Nationality updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

