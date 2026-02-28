from typing import Optional, Any
from sqlalchemy.orm import Session
from app.backend.db.models import DiversityCriterionModel


def _serialize_date(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v) if v else None


def _row_to_dict(r: DiversityCriterionModel) -> dict:
    return {
        "id": r.id,
        "key": r.key,
        "label": r.label,
        "sort_order": r.sort_order,
        "added_date": _serialize_date(r.added_date),
        "updated_date": _serialize_date(r.updated_date),
        "deleted_date": _serialize_date(r.deleted_date),
    }


class DiversityCriterionClass:
    def __init__(self, db: Session):
        self.db = db

    def get(self) -> Any:
        """Lista criterios activos (deleted_date is None), ordenados por sort_order."""
        try:
            rows = (
                self.db.query(DiversityCriterionModel)
                .filter(DiversityCriterionModel.deleted_date.is_(None))
                .order_by(DiversityCriterionModel.sort_order)
                .all()
            )
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene un criterio por id."""
        try:
            row = self.db.query(DiversityCriterionModel).filter(DiversityCriterionModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}
