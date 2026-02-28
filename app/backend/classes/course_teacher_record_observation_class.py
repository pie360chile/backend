"""Lógica para course_teacher_record_observations (observaciones por asignatura, 1 por course_id+subject_id)."""

from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.backend.db.models import CourseTeacherRecordObservationModel


def _date_str(v, fmt="%Y-%m-%d %H:%M:%S"):
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if hasattr(v, "strftime"):
        return v.strftime(fmt)
    return str(v)


def _row_to_dict(r: CourseTeacherRecordObservationModel) -> dict:
    return {
        "id": r.id,
        "course_id": r.course_id,
        "subject_id": r.subject_id,
        "observations": r.observations,
        "created_at": _date_str(r.created_at),
        "updated_at": _date_str(r.updated_at),
    }


class CourseTeacherRecordObservationClass:
    def __init__(self, db: Session):
        self.db = db

    def get_by_course_id(self, course_id: int) -> Any:
        """Lista observaciones del curso (una por subject_id)."""
        try:
            rows = (
                self.db.query(CourseTeacherRecordObservationModel)
                .filter(CourseTeacherRecordObservationModel.course_id == course_id)
                .order_by(CourseTeacherRecordObservationModel.subject_id)
                .all()
            )
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_course_subject(self, course_id: int, subject_id: int) -> Any:
        """Obtiene la observación para (course_id, subject_id) si existe."""
        try:
            row = (
                self.db.query(CourseTeacherRecordObservationModel)
                .filter(
                    CourseTeacherRecordObservationModel.course_id == course_id,
                    CourseTeacherRecordObservationModel.subject_id == subject_id,
                )
                .first()
            )
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def get_by_id(self, id: int) -> Any:
        """Obtiene una observación por id."""
        try:
            row = self.db.query(CourseTeacherRecordObservationModel).filter(CourseTeacherRecordObservationModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        """Crea o actualiza observación por (course_id, subject_id). Una sola fila por (curso, asignatura)."""
        try:
            course_id = int(data.get("course_id"))
            subject_id = int(data.get("subject_id"))
            observations = (data.get("observations") or "").strip() or None
            now = datetime.now()

            row = (
                self.db.query(CourseTeacherRecordObservationModel)
                .filter(
                    CourseTeacherRecordObservationModel.course_id == course_id,
                    CourseTeacherRecordObservationModel.subject_id == subject_id,
                )
                .first()
            )
            if row:
                row.observations = observations
                row.updated_at = now
                self.db.commit()
                self.db.refresh(row)
                return {"status": "success", "message": "Observación actualizada.", "id": row.id, "data": _row_to_dict(row)}
            row = CourseTeacherRecordObservationModel(
                course_id=course_id,
                subject_id=subject_id,
                observations=observations,
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Observación creada.", "id": row.id, "data": _row_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza observación por id (solo observations)."""
        try:
            row = self.db.query(CourseTeacherRecordObservationModel).filter(CourseTeacherRecordObservationModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "observations" in data:
                row.observations = (data.get("observations") or "").strip() or None
            row.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro actualizado.", "id": id, "data": _row_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
