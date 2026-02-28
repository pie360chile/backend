from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.backend.db.models import SubjectModel


def _row_to_dict(r: SubjectModel) -> dict:
    return {
        "id": r.id,
        "school_id": r.school_id,
        "subject": r.subject,
        "added_date": r.added_date.isoformat() if r.added_date else None,
        "updated_date": r.updated_date.isoformat() if r.updated_date else None,
        "deleted_date": r.deleted_date.isoformat() if r.deleted_date else None,
    }


class SubjectClass:
    def __init__(self, db: Session):
        self.db = db

    def get(self, school_id: Optional[int] = None) -> Any:
        """Lista registros activos (deleted_date is None). Filtro opcional por school_id (-1 o None = no filtrar)."""
        try:
            q = (
                self.db.query(SubjectModel)
                .filter(SubjectModel.deleted_date.is_(None))
            )
            if school_id is not None and school_id != -1:
                q = q.filter(SubjectModel.school_id == school_id)
            rows = q.all()
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene un registro por id."""
        try:
            row = self.db.query(SubjectModel).filter(SubjectModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        """Crea un registro en subjects."""
        try:
            now = datetime.now()
            row = SubjectModel(
                school_id=data.get("school_id"),
                subject=data.get("subject"),
                added_date=now,
                updated_date=now,
                deleted_date=None,
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
            row = self.db.query(SubjectModel).filter(SubjectModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "school_id" in data:
                row.school_id = data["school_id"]
            if "subject" in data:
                row.subject = data["subject"]
            row.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro actualizado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        """Borrado lógico: setea deleted_date."""
        try:
            row = self.db.query(SubjectModel).filter(SubjectModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = datetime.now()
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
