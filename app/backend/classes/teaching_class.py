from datetime import datetime
from app.backend.db.models import TeachingModel, ProfessionalTeachingCourseModel

class TeachingClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, school_id=None, teaching_name=None):
        try:
            print(f"========== DEBUG GET_ALL TEACHINGS ==========")
            print(f"page: {page}, items_per_page: {items_per_page}")
            print(f"school_id: {school_id}, teaching_name: {teaching_name}")
            
            query = self.db.query(
                TeachingModel.id,
                TeachingModel.school_id,
                TeachingModel.teaching_type_id,
                TeachingModel.teaching_name,
                TeachingModel.added_date,
                TeachingModel.updated_date
            ).filter(TeachingModel.deleted_status_id == 0)

            # Filtrar por school_id si se proporciona
            if school_id:
                query = query.filter(TeachingModel.school_id == school_id)

            # Aplicar filtro de búsqueda si se proporciona teaching_name
            if teaching_name and teaching_name.strip():
                query = query.filter(TeachingModel.teaching_name.like(f"%{teaching_name.strip()}%"))

            query = query.order_by(TeachingModel.id)

            if page > 0:
                total_items = query.count()
                print(f"Total items found: {total_items}")
                total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 0

                if total_items == 0:
                    print("No teachings found for the criteria")
                    print("===========================================")

                    return {
                        "total_items": 0,
                        "total_pages": 0,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                if page < 1 or page > total_pages:
                    return {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                serialized_data = [{
                    "id": teaching.id,
                    "school_id": teaching.school_id,
                    "teaching_type_id": teaching.teaching_type_id,
                    "teaching_name": teaching.teaching_name,
                    "added_date": teaching.added_date.strftime("%Y-%m-%d %H:%M:%S") if teaching.added_date else None,
                    "updated_date": teaching.updated_date.strftime("%Y-%m-%d %H:%M:%S") if teaching.updated_date else None
                } for teaching in data]

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
                    "id": teaching.id,
                    "school_id": teaching.school_id,
                    "teaching_type_id": teaching.teaching_type_id,
                    "teaching_name": teaching.teaching_name,
                    "added_date": teaching.added_date.strftime("%Y-%m-%d %H:%M:%S") if teaching.added_date else None,
                    "updated_date": teaching.updated_date.strftime("%Y-%m-%d %H:%M:%S") if teaching.updated_date else None
                } for teaching in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_all_list(self, school_id=None):
        """Retorna todos los teachings sin paginación ni búsqueda"""
        try:
            query = self.db.query(
                TeachingModel.id,
                TeachingModel.school_id,
                TeachingModel.teaching_type_id,
                TeachingModel.teaching_name,
                TeachingModel.added_date,
                TeachingModel.updated_date
            ).filter(TeachingModel.deleted_status_id == 0)

            # Filtrar por school_id si se proporciona
            if school_id:
                query = query.filter(TeachingModel.school_id == school_id)

            query = query.order_by(TeachingModel.id)
            
            data = query.all()

            serialized_data = [{
                "id": teaching.id,
                "school_id": teaching.school_id,
                "teaching_type_id": teaching.teaching_type_id,
                "teaching_name": teaching.teaching_name,
                "added_date": teaching.added_date.strftime("%Y-%m-%d %H:%M:%S") if teaching.added_date else None,
                "updated_date": teaching.updated_date.strftime("%Y-%m-%d %H:%M:%S") if teaching.updated_date else None
            } for teaching in data]

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(TeachingModel).filter(TeachingModel.id == id).first()

            if data_query:
                teaching_data = {
                    "id": data_query.id,
                    "school_id": data_query.school_id,
                    "teaching_type_id": data_query.teaching_type_id,
                    "teaching_name": data_query.teaching_name,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"teaching_data": teaching_data}

            else:
                return {"error": "No se encontraron datos para el teaching especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, teaching_inputs):
        try:
            new_teaching = TeachingModel(
                school_id=teaching_inputs.get('school_id'),
                teaching_type_id=teaching_inputs.get('teaching_type_id'),
                teaching_name=teaching_inputs['teaching_name'],
                deleted_status_id=0,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_teaching)
            self.db.commit()
            self.db.refresh(new_teaching)

            return {
                "status": "success",
                "message": "Teaching created successfully",
                "teaching_id": new_teaching.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(TeachingModel).filter(TeachingModel.id == id).first()
            if data:
                # Marcar como eliminado en professionals_teachings_courses
                self.db.query(ProfessionalTeachingCourseModel).filter(
                    ProfessionalTeachingCourseModel.teaching_id == id
                ).update({
                    "deleted_status_id": 1,
                    "updated_date": datetime.now()
                })
                
                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Teaching deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, teaching_inputs):
        try:
            existing_teaching = self.db.query(TeachingModel).filter(TeachingModel.id == id).one_or_none()

            if not existing_teaching:
                return {"status": "error", "message": "No data found"}

            for key, value in teaching_inputs.items():
                setattr(existing_teaching, key, value)

            existing_teaching.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_teaching)

            return {"status": "success", "message": "Teaching updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

