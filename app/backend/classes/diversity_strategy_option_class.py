from typing import Optional, Any
from sqlalchemy.orm import Session
from app.backend.db.models import DiversityStrategyOptionModel


def _serialize_date(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v) if v else None


def _row_to_dict(r: DiversityStrategyOptionModel) -> dict:
    return {
        "id": r.id,
        "diversity_criterion_id": r.diversity_criterion_id,
        "label": r.label,
        "sort_order": r.sort_order,
        "added_date": _serialize_date(r.added_date),
        "updated_date": _serialize_date(r.updated_date),
        "deleted_date": _serialize_date(r.deleted_date),
    }


class DiversityStrategyOptionClass:
    def __init__(self, db: Session):
        self.db = db

    def get(self, diversity_criterion_id: Optional[int] = None) -> Any:
        """Lista opciones activas. Filtro opcional por diversity_criterion_id (-1 o None = no filtrar)."""
        try:
            q = (
                self.db.query(DiversityStrategyOptionModel)
                .filter(DiversityStrategyOptionModel.deleted_date.is_(None))
            )
            if diversity_criterion_id is not None and diversity_criterion_id != -1:
                q = q.filter(DiversityStrategyOptionModel.diversity_criterion_id == diversity_criterion_id)
            rows = q.order_by(DiversityStrategyOptionModel.sort_order).all()
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene una opción por id."""
        try:
            row = self.db.query(DiversityStrategyOptionModel).filter(DiversityStrategyOptionModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}
