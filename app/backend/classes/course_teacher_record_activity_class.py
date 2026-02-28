"""Lógica para course_teacher_record_activities (actividades por asignatura, varias por materia)."""

from datetime import datetime, date
from typing import Optional, Any, List
import json
from sqlalchemy.orm import Session
from app.backend.db.models import CourseTeacherRecordActivityModel


def _date_str(v, fmt="%Y-%m-%d %H:%M:%S"):
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if hasattr(v, "strftime"):
        return v.strftime(fmt)
    return str(v)


def _parse_date(s: Optional[str]) -> Optional[date]:
    if s is None or (isinstance(s, str) and not s.strip()):
        return None
    if isinstance(s, date):
        return s
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _parse_teacher_names(v) -> Optional[str]:
    """Serializa lista de nombres a JSON string para la BD."""
    if v is None:
        return None
    if isinstance(v, list):
        return json.dumps(v, ensure_ascii=False) if v else None
    if isinstance(v, str):
        try:
            json.loads(v)
            return v
        except (json.JSONDecodeError, TypeError):
            return json.dumps([v], ensure_ascii=False)
    return None


def _load_teacher_names(v) -> Optional[List[str]]:
    """Deserializa teacher_names desde la BD."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, list):
        return v
    try:
        return json.loads(v) if isinstance(v, str) else None
    except (json.JSONDecodeError, TypeError):
        return None


def _row_to_dict(r: CourseTeacherRecordActivityModel) -> dict:
    return {
        "id": r.id,
        "course_id": r.course_id,
        "subject_id": r.subject_id,
        "date": r.date.isoformat() if r.date else None,
        "pedagogical_hours": float(r.pedagogical_hours) if r.pedagogical_hours is not None else 0,
        "teacher_names": _load_teacher_names(r.teacher_names),
        "description": r.description,
        "created_at": _date_str(r.created_at),
        "updated_at": _date_str(r.updated_at),
    }


class CourseTeacherRecordActivityClass:
    def __init__(self, db: Session):
        self.db = db

    def get_by_course_id(self, course_id: int, subject_id: Optional[int] = None) -> Any:
        """Lista actividades del curso; opcionalmente filtradas por subject_id."""
        try:
            q = self.db.query(CourseTeacherRecordActivityModel).filter(
                CourseTeacherRecordActivityModel.course_id == course_id,
            )
            if subject_id is not None and subject_id != -1:
                q = q.filter(CourseTeacherRecordActivityModel.subject_id == subject_id)
            rows = q.order_by(CourseTeacherRecordActivityModel.date.desc(), CourseTeacherRecordActivityModel.id.desc()).all()
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene una actividad por id."""
        try:
            row = self.db.query(CourseTeacherRecordActivityModel).filter(CourseTeacherRecordActivityModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        """Crea una actividad."""
        try:
            course_id = int(data.get("course_id"))
            subject_id = int(data.get("subject_id"))
            date_val = _parse_date(data.get("date"))
            if date_val is None:
                return {"status": "error", "message": "date es requerido y debe ser una fecha válida (YYYY-MM-DD)."}
            pedagogical_hours = data.get("pedagogical_hours")
            if pedagogical_hours is None:
                pedagogical_hours = 0
            else:
                pedagogical_hours = float(pedagogical_hours)
            teacher_names = _parse_teacher_names(data.get("teacher_names"))
            description = (data.get("description") or "").strip() or None
            now = datetime.now()

            row = CourseTeacherRecordActivityModel(
                course_id=course_id,
                subject_id=subject_id,
                date=date_val,
                pedagogical_hours=pedagogical_hours,
                teacher_names=teacher_names,
                description=description,
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Actividad creada.", "id": row.id, "data": _row_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza una actividad por id."""
        try:
            row = self.db.query(CourseTeacherRecordActivityModel).filter(CourseTeacherRecordActivityModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "date" in data:
                d = _parse_date(data["date"])
                if d is not None:
                    row.date = d
            if "pedagogical_hours" in data:
                row.pedagogical_hours = float(data["pedagogical_hours"])
            if "teacher_names" in data:
                row.teacher_names = _parse_teacher_names(data["teacher_names"])
            if "description" in data:
                row.description = (data.get("description") or "").strip() or None
            row.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro actualizado.", "id": id, "data": _row_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        """Elimina físicamente la actividad."""
        try:
            row = self.db.query(CourseTeacherRecordActivityModel).filter(CourseTeacherRecordActivityModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            self.db.delete(row)
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado.", "id": id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
