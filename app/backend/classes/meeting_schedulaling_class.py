from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.backend.db.models import MeetingSchedulalingModel


def _parse_date(value):
    """Convierte string a date si es necesario."""
    if value is None:
        return None
    if hasattr(value, "year"):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    return None


def _row_to_dict(r: MeetingSchedulalingModel) -> dict:
    return {
        "id": r.id,
        "school_id": r.school_id,
        "course_id": r.course_id,
        "meeting_date": r.meeting_date.isoformat() if r.meeting_date else None,
        "meeting_time": r.meeting_time,
        "added_date": r.added_date.isoformat() if r.added_date else None,
        "updated_date": r.updated_date.isoformat() if r.updated_date else None,
        "deleted_date": r.deleted_date.isoformat() if r.deleted_date else None,
    }


class MeetingSchedulalingClass:
    def __init__(self, db: Session):
        self.db = db

    def get(
        self,
        school_id: Optional[int] = None,
        course_id: Optional[int] = None,
    ) -> Any:
        """Lista registros activos (deleted_date is None). Filtros opcionales (-1 o None = no filtrar)."""
        try:
            q = (
                self.db.query(MeetingSchedulalingModel)
                .filter(MeetingSchedulalingModel.deleted_date.is_(None))
            )
            if school_id is not None and school_id != -1:
                q = q.filter(MeetingSchedulalingModel.school_id == school_id)
            if course_id is not None and course_id != -1:
                q = q.filter(MeetingSchedulalingModel.course_id == course_id)
            rows = q.all()
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene un registro por id."""
        try:
            row = self.db.query(MeetingSchedulalingModel).filter(MeetingSchedulalingModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        """Crea un registro en meeting_schedualings."""
        try:
            now = datetime.now()
            meeting_date = _parse_date(data.get("meeting_date"))
            row = MeetingSchedulalingModel(
                school_id=data.get("school_id"),
                course_id=data.get("course_id"),
                meeting_date=meeting_date,
                meeting_time=data.get("meeting_time"),
                added_date=now,
                updated_date=now,
                deleted_date=None,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro creado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza un registro; solo los campos enviados."""
        try:
            row = self.db.query(MeetingSchedulalingModel).filter(MeetingSchedulalingModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "school_id" in data and data["school_id"] is not None:
                row.school_id = data["school_id"]
            if "course_id" in data and data["course_id"] is not None:
                row.course_id = data["course_id"]
            if "meeting_date" in data:
                row.meeting_date = _parse_date(data["meeting_date"])
            if "meeting_time" in data:
                row.meeting_time = data["meeting_time"]
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
            row = self.db.query(MeetingSchedulalingModel).filter(MeetingSchedulalingModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = datetime.now()
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
