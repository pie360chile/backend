from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.backend.db.models import DiversifiedStrategyModel


def _row_to_dict(r: DiversifiedStrategyModel) -> dict:
    return {
        "id": r.id,
        "course_id": r.course_id,
        "planning_learning_styles": r.planning_learning_styles,
        "planning_strengths": r.planning_strengths,
        "planning_support_needs": r.planning_support_needs,
        "added_date": r.added_date.isoformat() if r.added_date else None,
        "updated_date": r.updated_date.isoformat() if r.updated_date else None,
    }


class DiversifiedStrategyClass:
    def __init__(self, db: Session):
        self.db = db

    def get(self, course_id: Optional[int] = None) -> Any:
        """Lista registros. Filtro opcional por course_id (-1 o None = no filtrar)."""
        try:
            q = self.db.query(DiversifiedStrategyModel)
            if course_id is not None and course_id != -1:
                q = q.filter(DiversifiedStrategyModel.course_id == course_id)
            rows = q.all()
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene un registro por id."""
        try:
            row = self.db.query(DiversifiedStrategyModel).filter(DiversifiedStrategyModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def get_by_course_id(self, course_id: int) -> Any:
        """Obtiene el registro por course_id (uno por curso)."""
        try:
            row = (
                self.db.query(DiversifiedStrategyModel)
                .filter(DiversifiedStrategyModel.course_id == course_id)
                .first()
            )
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        """Si ya existe un registro con el mismo course_id → UPDATE; si no existe → INSERT (crear)."""
        try:
            now = datetime.now()
            course_id = data.get("course_id")
            row = (
                self.db.query(DiversifiedStrategyModel)
                .filter(DiversifiedStrategyModel.course_id == course_id)
                .first()
            )
            if row:
                row.planning_learning_styles = data.get("planning_learning_styles")
                row.planning_strengths = data.get("planning_strengths")
                row.planning_support_needs = data.get("planning_support_needs")
                row.updated_date = now
                self.db.commit()
                self.db.refresh(row)
                return {"status": "success", "message": "Registro actualizado.", "id": row.id, "data": _row_to_dict(row)}
            row = DiversifiedStrategyModel(
                course_id=course_id,
                planning_learning_styles=data.get("planning_learning_styles"),
                planning_strengths=data.get("planning_strengths"),
                planning_support_needs=data.get("planning_support_needs"),
                added_date=now,
                updated_date=now,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro creado.", "id": row.id, "data": _row_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza un registro por id; solo los campos enviados."""
        try:
            row = self.db.query(DiversifiedStrategyModel).filter(DiversifiedStrategyModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "course_id" in data:
                row.course_id = data["course_id"]
            if "planning_learning_styles" in data:
                row.planning_learning_styles = data["planning_learning_styles"]
            if "planning_strengths" in data:
                row.planning_strengths = data["planning_strengths"]
            if "planning_support_needs" in data:
                row.planning_support_needs = data["planning_support_needs"]
            row.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro actualizado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        """Elimina físicamente el registro."""
        try:
            row = self.db.query(DiversifiedStrategyModel).filter(DiversifiedStrategyModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            self.db.delete(row)
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
