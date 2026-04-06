from datetime import datetime

from sqlalchemy import false as sql_false

from app.backend.db.models import SpecialEducationalNeedModel


def _serialize_need(need):
    return {
        "id": need.id,
        "school_id": need.school_id,
        "special_educational_need_type_id": need.special_educational_need_type_id,
        "deleted_status_id": need.deleted_status_id,
        "special_educational_needs": need.special_educational_needs,
        "added_date": need.added_date.strftime("%Y-%m-%d %H:%M:%S") if need.added_date else None,
        "updated_date": need.updated_date.strftime("%Y-%m-%d %H:%M:%S") if need.updated_date else None,
    }


class SpecialEducationalNeedClass:
    def __init__(self, db):
        self.db = db

    def _scope_filter(self, query, school_id):
        """Only rows for the active school. No school in session → empty set (no cross-tenant reads)."""
        if school_id is not None:
            return query.filter(SpecialEducationalNeedModel.school_id == school_id)
        return query.filter(sql_false())

    def get_all(
        self,
        page=0,
        items_per_page=10,
        special_educational_needs=None,
        special_educational_need_type_id=None,
        school_id=None,
    ):
        try:
            query = self.db.query(SpecialEducationalNeedModel)

            query = query.filter(SpecialEducationalNeedModel.deleted_status_id == 0)
            query = self._scope_filter(query, school_id)

            if special_educational_need_type_id is not None:
                query = query.filter(SpecialEducationalNeedModel.special_educational_need_type_id == special_educational_need_type_id)
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
                        "data": [],
                    }

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                serialized_data = [_serialize_need(need) for need in data]

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data,
                }

            data = query.all()
            return [_serialize_need(need) for need in data]

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get(self, id, school_id=None):
        try:
            query = self.db.query(SpecialEducationalNeedModel).filter(
                SpecialEducationalNeedModel.id == id,
                SpecialEducationalNeedModel.deleted_status_id == 0,
            )
            query = self._scope_filter(query, school_id)
            need = query.first()

            if need:
                return _serialize_need(need)
            return {"status": "error", "message": "No data found"}

        except Exception as e:
            error_message = str(e)
            return {"error": error_message}

    def store(self, need_inputs, school_id=None):
        try:
            sid = need_inputs.get("school_id")
            if sid is not None:
                sid = int(sid)
            if school_id is not None:
                sid = int(school_id)

            new_need = SpecialEducationalNeedModel(
                school_id=sid,
                special_educational_need_type_id=need_inputs.get("special_educational_need_type_id"),
                deleted_status_id=0,
                special_educational_needs=need_inputs.get("special_educational_needs"),
                added_date=datetime.now(),
                updated_date=datetime.now(),
            )

            self.db.add(new_need)
            self.db.commit()
            self.db.refresh(new_need)

            return {
                "status": "success",
                "message": "Special educational need created successfully",
                "need_id": new_need.id,
            }

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, need_inputs, school_id=None):
        try:
            query = self.db.query(SpecialEducationalNeedModel).filter(SpecialEducationalNeedModel.id == id)
            query = self._scope_filter(query, school_id)
            existing_need = query.one_or_none()

            if not existing_need:
                return {"status": "error", "message": "No data found"}

            if "special_educational_need_type_id" in need_inputs:
                existing_need.special_educational_need_type_id = need_inputs["special_educational_need_type_id"]
            if "special_educational_needs" in need_inputs:
                existing_need.special_educational_needs = need_inputs["special_educational_needs"]
            if "school_id" in need_inputs and need_inputs["school_id"] is not None:
                existing_need.school_id = need_inputs["school_id"]

            existing_need.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_need)

            return {"status": "success", "message": "Special educational need updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id, school_id=None):
        try:
            query = self.db.query(SpecialEducationalNeedModel).filter(
                SpecialEducationalNeedModel.id == id,
                SpecialEducationalNeedModel.deleted_status_id == 0,
            )
            query = self._scope_filter(query, school_id)
            need = query.first()

            if need:
                need.deleted_status_id = 1
                need.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Special educational need deleted successfully"}
            return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}
