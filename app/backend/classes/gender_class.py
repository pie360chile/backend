from datetime import datetime
from app.backend.db.models import GenderModel

class GenderClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, gender=None):
        try:
            query = self.db.query(
                GenderModel.id,
                GenderModel.gender,
                GenderModel.added_date,
                GenderModel.updated_date
            ).filter(GenderModel.deleted_status_id == 0)

            # Aplicar filtro de búsqueda si se proporciona gender
            if gender and gender.strip():
                query = query.filter(GenderModel.gender.like(f"%{gender.strip()}%"))

            query = query.order_by(GenderModel.id)

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
                    "id": item.id,
                    "gender": item.gender,
                    "added_date": item.added_date.strftime("%Y-%m-%d %H:%M:%S") if item.added_date else None,
                    "updated_date": item.updated_date.strftime("%Y-%m-%d %H:%M:%S") if item.updated_date else None
                } for item in data]

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
                    "id": item.id,
                    "gender": item.gender,
                    "added_date": item.added_date.strftime("%Y-%m-%d %H:%M:%S") if item.added_date else None,
                    "updated_date": item.updated_date.strftime("%Y-%m-%d %H:%M:%S") if item.updated_date else None
                } for item in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_all_list(self):
        """Retorna todos los genders sin paginación ni búsqueda"""
        try:
            query = self.db.query(
                GenderModel.id,
                GenderModel.gender,
                GenderModel.added_date,
                GenderModel.updated_date
            ).filter(GenderModel.deleted_status_id == 0).order_by(GenderModel.id)
            
            data = query.all()

            serialized_data = [{
                "id": item.id,
                "gender": item.gender,
                "added_date": item.added_date.strftime("%Y-%m-%d %H:%M:%S") if item.added_date else None,
                "updated_date": item.updated_date.strftime("%Y-%m-%d %H:%M:%S") if item.updated_date else None
            } for item in data]

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(GenderModel).filter(GenderModel.id == id).first()

            if data_query:
                item_data = {
                    "id": data_query.id,
                    "gender": data_query.gender,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"item_data": item_data}

            else:
                return {"error": "No se encontraron datos para el gender especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, item_inputs):
        try:
            new_item = GenderModel(
                gender=item_inputs['gender'],
                deleted_status_id=0,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_item)
            self.db.commit()
            self.db.refresh(new_item)

            return {
                "status": "success",
                "message": "Gender created successfully",
                "item_id": new_item.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(GenderModel).filter(GenderModel.id == id).first()
            if data:
                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Gender deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, item_inputs):
        try:
            existing_item = self.db.query(GenderModel).filter(GenderModel.id == id).one_or_none()

            if not existing_item:
                return {"status": "error", "message": "No data found"}

            for key, value in item_inputs.items():
                setattr(existing_item, key, value)

            existing_item.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_item)

            return {"status": "success", "message": "Gender updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

