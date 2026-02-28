from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.backend.db.models import RegularTeacherDiversifiedStrategyModel


def _row_to_dict(r: RegularTeacherDiversifiedStrategyModel) -> dict:
    return {
        "id": r.id,
        "school_id": r.school_id,
        "course_id": r.course_id,
        "subject_id": r.subject_id,
        "strategy": r.strategy,
        "period": r.period,
        "criteria": r.criteria,
        "added_date": r.added_date.isoformat() if r.added_date else None,
        "updated_date": r.updated_date.isoformat() if r.updated_date else None,
    }


class RegularTeacherDiversifiedStrategyClass:
    def __init__(self, db: Session):
        self.db = db

    def get(
        self,
        school_id: Optional[int] = None,
        course_id: Optional[int] = None,
        subject_id: Optional[int] = None,
    ) -> Any:
        """Lista registros. Filtros opcionales por school_id, course_id y subject_id (-1 o None = no filtrar)."""
        try:
            q = self.db.query(RegularTeacherDiversifiedStrategyModel)
            if school_id is not None and school_id != -1:
                q = q.filter(RegularTeacherDiversifiedStrategyModel.school_id == school_id)
            if course_id is not None and course_id != -1:
                q = q.filter(RegularTeacherDiversifiedStrategyModel.course_id == course_id)
            if subject_id is not None and subject_id != -1:
                q = q.filter(RegularTeacherDiversifiedStrategyModel.subject_id == subject_id)
            rows = q.all()
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene un registro por id."""
        try:
            row = self.db.query(RegularTeacherDiversifiedStrategyModel).filter(RegularTeacherDiversifiedStrategyModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def get_by_course_id(self, course_id: int) -> Any:
        """Obtiene la lista de registros por course_id."""
        try:
            rows = (
                self.db.query(RegularTeacherDiversifiedStrategyModel)
                .filter(RegularTeacherDiversifiedStrategyModel.course_id == course_id)
                .all()
            )
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def store(self, data: dict) -> Any:
        """Crea un nuevo registro en regular_teacher_diversified_strategies. school_id del body o sesión."""
        try:
            now = datetime.now()
            row = RegularTeacherDiversifiedStrategyModel(
                school_id=data.get("school_id"),
                course_id=data.get("course_id"),
                subject_id=data.get("subject_id"),
                strategy=data.get("strategy"),
                period=data.get("period"),
                criteria=data.get("criteria"),
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
            row = self.db.query(RegularTeacherDiversifiedStrategyModel).filter(RegularTeacherDiversifiedStrategyModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "school_id" in data:
                row.school_id = data["school_id"]
            if "course_id" in data:
                row.course_id = data["course_id"]
            if "subject_id" in data:
                row.subject_id = data["subject_id"]
            if "strategy" in data:
                row.strategy = data["strategy"]
            if "period" in data:
                row.period = data["period"]
            if "criteria" in data:
                row.criteria = data["criteria"]
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
            row = self.db.query(RegularTeacherDiversifiedStrategyModel).filter(RegularTeacherDiversifiedStrategyModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            self.db.delete(row)
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
