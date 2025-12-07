from app.backend.db.models import CareerTypeModel
from datetime import datetime

class CareerTypeClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, career_type=None):
        try:
            query = self.db.query(CareerTypeModel)

            # Filtrar por tipo de carrera si se proporciona
            if career_type:
                query = query.filter(CareerTypeModel.career_type.like(f'%{career_type}%'))

            # Ordenar por tipo de carrera
            query = query.order_by(CareerTypeModel.career_type.asc())

            # Contar total de registros
            total_items = query.count()

            # Aplicar paginación
            if items_per_page is not None:
                offset = page * items_per_page
                career_types = query.offset(offset).limit(items_per_page).all()
            else:
                career_types = query.all()

            if not career_types:
                return {
                    "status": "error",
                    "message": "No data found",
                    "data": None,
                    "total_items": 0,
                    "total_pages": 0,
                    "current_page": page
                }

            # Calcular total de páginas
            if items_per_page is not None:
                total_pages = (total_items + items_per_page - 1) // items_per_page
            else:
                total_pages = 1

            # Convertir a diccionarios
            career_types_list = []
            for career in career_types:
                career_dict = {
                    "id": career.id,
                    "career_type": career.career_type,
                    "added_date": career.added_date.strftime('%Y-%m-%d %H:%M:%S') if career.added_date else None,
                    "updated_date": career.updated_date.strftime('%Y-%m-%d %H:%M:%S') if career.updated_date else None
                }
                career_types_list.append(career_dict)

            return {
                "status": "success",
                "data": career_types_list,
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get(self, career_type_id):
        try:
            career_type = self.db.query(CareerTypeModel).filter(
                CareerTypeModel.id == career_type_id
            ).first()

            if not career_type:
                return {
                    "status": "error",
                    "message": "Career type not found"
                }

            career_dict = {
                "id": career_type.id,
                "career_type": career_type.career_type,
                "added_date": career_type.added_date.strftime('%Y-%m-%d %H:%M:%S') if career_type.added_date else None,
                "updated_date": career_type.updated_date.strftime('%Y-%m-%d %H:%M:%S') if career_type.updated_date else None
            }

            return career_dict

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def store(self, career_type_data):
        try:
            new_career_type = CareerTypeModel(
                career_type=career_type_data.get('career_type'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_career_type)
            self.db.commit()
            self.db.refresh(new_career_type)

            return {
                "status": "success",
                "message": "Career type created successfully",
                "data": {
                    "id": new_career_type.id
                }
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def update(self, career_type_id, career_type_data):
        try:
            career_type = self.db.query(CareerTypeModel).filter(
                CareerTypeModel.id == career_type_id
            ).first()

            if not career_type:
                return {
                    "status": "error",
                    "message": "Career type not found"
                }

            # Actualizar campos
            if career_type_data.get('career_type') is not None:
                career_type.career_type = career_type_data.get('career_type')

            career_type.updated_date = datetime.now()

            self.db.commit()

            return {
                "status": "success",
                "message": "Career type updated successfully"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def delete(self, career_type_id):
        try:
            career_type = self.db.query(CareerTypeModel).filter(
                CareerTypeModel.id == career_type_id
            ).first()

            if not career_type:
                return {
                    "status": "error",
                    "message": "Career type not found"
                }

            # Hard delete
            self.db.delete(career_type)
            self.db.commit()

            return {
                "status": "success",
                "message": "Career type deleted successfully"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
