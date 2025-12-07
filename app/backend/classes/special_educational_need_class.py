from datetime import datetime
from app.backend.db.models import SpecialEducationalNeedModel

class SpecialEducationalNeedClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, special_educational_needs=None):
        try:
            query = self.db.query(SpecialEducationalNeedModel)

            # Filtrar solo registros no eliminados
            query = query.filter(SpecialEducationalNeedModel.deleted_status_id == 0)

            # Aplicar filtro de búsqueda
            if special_educational_needs and special_educational_needs.strip():
                query = query.filter(SpecialEducationalNeedModel.special_educational_needs.like(f"%{special_educational_needs.strip()}%"))

            query = query.order_by(SpecialEducationalNeedModel.special_educational_needs.asc())

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
                    "id": need.id,
                    "deleted_status_id": need.deleted_status_id,
                    "special_educational_needs": need.special_educational_needs,
                    "added_date": need.added_date.strftime("%Y-%m-%d %H:%M:%S") if need.added_date else None,
                    "updated_date": need.updated_date.strftime("%Y-%m-%d %H:%M:%S") if need.updated_date else None
                } for need in data]

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
                    "id": need.id,
                    "deleted_status_id": need.deleted_status_id,
                    "special_educational_needs": need.special_educational_needs,
                    "added_date": need.added_date.strftime("%Y-%m-%d %H:%M:%S") if need.added_date else None,
                    "updated_date": need.updated_date.strftime("%Y-%m-%d %H:%M:%S") if need.updated_date else None
                } for need in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get(self, id):
        try:
            need = self.db.query(SpecialEducationalNeedModel).filter(
                SpecialEducationalNeedModel.id == id,
                SpecialEducationalNeedModel.deleted_status_id == 0
            ).first()

            if need:
                return {
                    "id": need.id,
                    "deleted_status_id": need.deleted_status_id,
                    "special_educational_needs": need.special_educational_needs,
                    "added_date": need.added_date.strftime("%Y-%m-%d %H:%M:%S") if need.added_date else None,
                    "updated_date": need.updated_date.strftime("%Y-%m-%d %H:%M:%S") if need.updated_date else None
                }
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            error_message = str(e)
            return {"error": error_message}

    def store(self, need_inputs):
        try:
            new_need = SpecialEducationalNeedModel(
                deleted_status_id=0,
                special_educational_needs=need_inputs.get('special_educational_needs'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_need)
            self.db.commit()
            self.db.refresh(new_need)

            return {
                "status": "success",
                "message": "Special educational need created successfully",
                "need_id": new_need.id
            }

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, need_inputs):
        try:
            existing_need = self.db.query(SpecialEducationalNeedModel).filter(
                SpecialEducationalNeedModel.id == id
            ).one_or_none()

            if not existing_need:
                return {"status": "error", "message": "No data found"}

            if 'special_educational_needs' in need_inputs:
                existing_need.special_educational_needs = need_inputs['special_educational_needs']

            existing_need.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_need)

            return {"status": "success", "message": "Special educational need updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id):
        try:
            need = self.db.query(SpecialEducationalNeedModel).filter(
                SpecialEducationalNeedModel.id == id,
                SpecialEducationalNeedModel.deleted_status_id == 0
            ).first()

            if need:
                need.deleted_status_id = 1
                need.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Special educational need deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}
