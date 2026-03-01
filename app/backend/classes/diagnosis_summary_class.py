from datetime import datetime
from app.backend.db.models import DiagnosisSummaryModel


def _serialize_row(row):
    return {
        "id": row.id,
        "school_id": row.school_id,
        "special_educational_need_id": row.special_educational_need_id,
        "course_id": row.course_id,
        "year_index": row.year_index,
        "available_slots": row.available_slots,
        "occupied_slots": row.occupied_slots,
        "added_date": row.added_date.strftime("%Y-%m-%d %H:%M:%S") if row.added_date else None,
        "updated_date": row.updated_date.strftime("%Y-%m-%d %H:%M:%S") if row.updated_date else None,
    }


class DiagnosisSummaryClass:
    def __init__(self, db):
        self.db = db

    def get_all(
        self,
        page=0,
        items_per_page=10,
        school_id=None,
        special_educational_need_id=None,
        course_id=None,
        year_index=None,
    ):
        try:
            query = self.db.query(DiagnosisSummaryModel)
            if school_id is not None:
                query = query.filter(DiagnosisSummaryModel.school_id == school_id)
            if special_educational_need_id is not None:
                query = query.filter(
                    DiagnosisSummaryModel.special_educational_need_id == special_educational_need_id
                )
            if course_id is not None:
                query = query.filter(DiagnosisSummaryModel.course_id == course_id)
            if year_index is not None:
                query = query.filter(DiagnosisSummaryModel.year_index == year_index)
            query = query.order_by(
                DiagnosisSummaryModel.school_id.asc(),
                DiagnosisSummaryModel.special_educational_need_id.asc(),
                DiagnosisSummaryModel.course_id.asc(),
                DiagnosisSummaryModel.year_index.asc(),
            )

            if page > 0 and items_per_page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page if items_per_page else 0
                if page < 1 or (total_pages and page > total_pages):
                    return {
                        "total_items": total_items,
                        "total_pages": total_pages or 1,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": [],
                    }
                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()
                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": [_serialize_row(r) for r in data],
                }
            data = query.all()
            return [_serialize_row(r) for r in data]
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get(self, id):
        try:
            row = self.db.query(DiagnosisSummaryModel).filter(DiagnosisSummaryModel.id == id).first()
            if row:
                return _serialize_row(row)
            return {"status": "error", "message": "No data found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def find_by_unique(self, school_id, special_educational_need_id, course_id, year_index):
        """Busca por clave única (school_id, special_educational_need_id, course_id, year_index)."""
        q = self.db.query(DiagnosisSummaryModel).filter(
            DiagnosisSummaryModel.special_educational_need_id == special_educational_need_id,
            DiagnosisSummaryModel.course_id == course_id,
            DiagnosisSummaryModel.year_index == year_index,
        )
        if school_id is None:
            q = q.filter(DiagnosisSummaryModel.school_id.is_(None))
        else:
            q = q.filter(DiagnosisSummaryModel.school_id == school_id)
        return q.first()

    def store(self, inputs):
        try:
            now = datetime.now()
            row = DiagnosisSummaryModel(
                school_id=inputs.get("school_id"),
                special_educational_need_id=inputs.get("special_educational_need_id"),
                course_id=inputs.get("course_id"),
                year_index=inputs.get("year_index", 0),
                available_slots=inputs.get("available_slots", 0),
                occupied_slots=inputs.get("occupied_slots", 0),
                added_date=now,
                updated_date=now,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Resumen de diagnóstico creado", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def store_or_update(self, inputs):
        """Si existe registro con la misma clave única, actualiza; si no, crea."""
        school_id = inputs.get("school_id")
        need_id = inputs.get("special_educational_need_id")
        course_id = inputs.get("course_id")
        year_index = inputs.get("year_index", 0)
        existing = self.find_by_unique(school_id, need_id, course_id, year_index)
        if existing:
            out = self.update(existing.id, inputs)
            if out.get("status") == "success":
                out["created"] = False
            return out
        out = self.store(inputs)
        if out.get("status") == "success":
            out["created"] = True
        return out

    def update(self, id, inputs):
        try:
            row = self.db.query(DiagnosisSummaryModel).filter(DiagnosisSummaryModel.id == id).first()
            if not row:
                return {"status": "error", "message": "No data found"}
            if "school_id" in inputs:
                row.school_id = inputs["school_id"]
            if "special_educational_need_id" in inputs:
                row.special_educational_need_id = inputs["special_educational_need_id"]
            if "course_id" in inputs:
                row.course_id = inputs["course_id"]
            if "year_index" in inputs:
                row.year_index = inputs["year_index"]
            if "available_slots" in inputs:
                row.available_slots = inputs["available_slots"]
            if "occupied_slots" in inputs:
                row.occupied_slots = inputs["occupied_slots"]
            row.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Resumen de diagnóstico actualizado", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id):
        try:
            row = self.db.query(DiagnosisSummaryModel).filter(DiagnosisSummaryModel.id == id).first()
            if not row:
                return {"status": "error", "message": "No data found"}
            self.db.delete(row)
            self.db.commit()
            return {"status": "success", "message": "Resumen de diagnóstico eliminado"}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
