from typing import Any

from sqlalchemy.orm import Session

from app.backend.db.models import CurriculumSubjectModel


def _row_to_dict(r: CurriculumSubjectModel) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "name_es": r.name_es,
        "category": r.category,
        "sort_order": r.sort_order,
        "is_active": bool(r.is_active),
    }


class CurriculumSubjectClass:
    def __init__(self, db: Session):
        self.db = db

    def get_list(self) -> Any:
        try:
            rows = (
                self.db.query(CurriculumSubjectModel)
                .filter(CurriculumSubjectModel.deleted_date.is_(None))
                .filter(CurriculumSubjectModel.is_active == 1)
                .order_by(CurriculumSubjectModel.sort_order.asc(), CurriculumSubjectModel.name_es.asc())
                .all()
            )
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}
