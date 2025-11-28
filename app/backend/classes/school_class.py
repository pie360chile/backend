from datetime import datetime
from app.backend.db.models import SchoolModel

class SchoolClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, school_name=None, customer_id=None):
        try:
            query = self.db.query(
                SchoolModel.id,
                SchoolModel.customer_id,
                SchoolModel.deleted_status_id,
                SchoolModel.school_name,
                SchoolModel.school_address,
                SchoolModel.director_name,
                SchoolModel.community_school_password,
                SchoolModel.added_date,
                SchoolModel.updated_date
            )

            # Filtrar solo registros activos (deleted_status_id = 0)
            query = query.filter(SchoolModel.deleted_status_id == 0)
            
            # Aplicar filtros de búsqueda
            if school_name and school_name.strip():
                query = query.filter(SchoolModel.school_name.like(f"%{school_name.strip()}%"))
            
            if customer_id:
                query = query.filter(SchoolModel.customer_id == customer_id)

            query = query.order_by(SchoolModel.id.desc())

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
                    "id": school.id,
                    "customer_id": school.customer_id,
                    "deleted_status_id": school.deleted_status_id,
                    "school_name": school.school_name,
                    "school_address": school.school_address,
                    "director_name": school.director_name,
                    "community_school_password": school.community_school_password,
                    "added_date": school.added_date.strftime("%Y-%m-%d %H:%M:%S") if school.added_date else None,
                    "updated_date": school.updated_date.strftime("%Y-%m-%d %H:%M:%S") if school.updated_date else None
                } for school in data]

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
                    "id": school.id,
                    "customer_id": school.customer_id,
                    "deleted_status_id": school.deleted_status_id,
                    "school_name": school.school_name,
                    "school_address": school.school_address,
                    "director_name": school.director_name,
                    "community_school_password": school.community_school_password,
                    "added_date": school.added_date.strftime("%Y-%m-%d %H:%M:%S") if school.added_date else None,
                    "updated_date": school.updated_date.strftime("%Y-%m-%d %H:%M:%S") if school.updated_date else None
                } for school in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, customer_id, school_id=None):
        try:
            filters = [
                SchoolModel.customer_id == customer_id,
                SchoolModel.deleted_status_id == 0
            ]
            
            if school_id:
                filters.append(SchoolModel.id == school_id)
            
            data_query = self.db.query(SchoolModel).filter(*filters).first()

            if data_query:
                school_data = {
                    "id": data_query.id,
                    "customer_id": data_query.customer_id,
                    "deleted_status_id": data_query.deleted_status_id,
                    "school_name": data_query.school_name,
                    "school_address": data_query.school_address,
                    "director_name": data_query.director_name,
                    "community_school_password": data_query.community_school_password,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"school_data": school_data}

            else:
                return {"error": "No se encontraron datos para la escuela especificada."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, school_inputs):
        try:
            new_school = SchoolModel(
                customer_id=school_inputs['customer_id'],
                deleted_status_id=0,
                school_name=school_inputs['school_name'],
                school_address=school_inputs['school_address'],
                director_name=school_inputs['director_name'],
                community_school_password=school_inputs['community_school_password'],
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_school)
            self.db.commit()
            self.db.refresh(new_school)

            return {
                "status": "success",
                "message": "School created successfully",
                "school_id": new_school.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(SchoolModel).filter(SchoolModel.id == id).first()
            if data:
                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "School deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, school_inputs):
        try:
            existing_school = self.db.query(SchoolModel).filter(
                SchoolModel.id == id
            ).one_or_none()

            if not existing_school:
                return {"status": "error", "message": "No data found"}

            # Actualizar solo los campos que están presentes y no son None
            if 'customer_id' in school_inputs and school_inputs['customer_id'] is not None:
                existing_school.customer_id = school_inputs['customer_id']
            if 'school_name' in school_inputs and school_inputs['school_name']:
                existing_school.school_name = school_inputs['school_name']
            if 'school_address' in school_inputs and school_inputs['school_address']:
                existing_school.school_address = school_inputs['school_address']
            if 'director_name' in school_inputs and school_inputs['director_name']:
                existing_school.director_name = school_inputs['director_name']
            if 'community_school_password' in school_inputs and school_inputs['community_school_password']:
                existing_school.community_school_password = school_inputs['community_school_password']

            existing_school.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_school)

            return {"status": "success", "message": "School updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
