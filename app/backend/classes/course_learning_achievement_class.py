"""Card 3: Registro de logros de aprendizaje por curso, estudiante y período (1, 2, 3)."""

from datetime import datetime
from typing import Optional, Any, List
from sqlalchemy.orm import Session
from app.backend.db.models import CourseLearningAchievementModel, StudentModel


VALID_PERIODS = (1, 2, 3)


def _serialize_date(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v) if v else None


def _row_to_dict(row: CourseLearningAchievementModel) -> dict:
    return {
        "id": row.id,
        "course_id": row.course_id,
        "student_id": row.student_id,
        "period_id": row.period_id,
        "achievements": row.achievements,
        "comments": row.comments,
        "created_at": _serialize_date(row.created_at),
        "updated_at": _serialize_date(row.updated_at),
    }


class CourseLearningAchievementClass:
    def __init__(self, db: Session):
        self.db = db

    def get_by_course_id(self, course_id: int, period_id: Optional[int] = None) -> Any:
        """Lista logros del curso; opcionalmente filtrados por period_id (1, 2 o 3)."""
        try:
            q = self.db.query(CourseLearningAchievementModel).filter(
                CourseLearningAchievementModel.course_id == course_id,
            )
            if period_id is not None and period_id in VALID_PERIODS:
                q = q.filter(CourseLearningAchievementModel.period_id == period_id)
            rows = q.order_by(
                CourseLearningAchievementModel.student_id.asc(),
                CourseLearningAchievementModel.period_id.asc(),
            ).all()
            student_ids = list({r.student_id for r in rows})
            names = {}
            if student_ids:
                for s in self.db.query(StudentModel).filter(StudentModel.id.in_(student_ids)).all():
                    n = (getattr(s, "names", "") or "") + " " + (getattr(s, "lastnames", "") or "")
                    names[s.id] = n.strip() or getattr(s, "name", None) or str(s.id)
            result = []
            for r in rows:
                d = _row_to_dict(r)
                d["student_name"] = names.get(r.student_id, "")
                result.append(d)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene un registro de logros por id."""
        try:
            row = self.db.query(CourseLearningAchievementModel).filter(CourseLearningAchievementModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def get_by_course_student_period(self, course_id: int, student_id: int, period_id: int) -> Any:
        """Obtiene el registro único por (course_id, student_id, period_id)."""
        try:
            if period_id not in VALID_PERIODS:
                return {"status": "error", "message": "period_id debe ser 1, 2 o 3.", "data": None}
            row = (
                self.db.query(CourseLearningAchievementModel)
                .filter(
                    CourseLearningAchievementModel.course_id == course_id,
                    CourseLearningAchievementModel.student_id == student_id,
                    CourseLearningAchievementModel.period_id == period_id,
                )
                .first()
            )
            if not row:
                return {"status": "success", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        """Crea o actualiza por (course_id, student_id, period_id)."""
        try:
            course_id = int(data.get("course_id"))
            student_id = int(data.get("student_id"))
            period_id = int(data.get("period_id"))
            if period_id not in VALID_PERIODS:
                return {"status": "error", "message": "period_id debe ser 1, 2 o 3.", "data": None}
            achievements = (data.get("achievements") or "").strip() or None
            comments = (data.get("comments") or "").strip() or None

            row = (
                self.db.query(CourseLearningAchievementModel)
                .filter(
                    CourseLearningAchievementModel.course_id == course_id,
                    CourseLearningAchievementModel.student_id == student_id,
                    CourseLearningAchievementModel.period_id == period_id,
                )
                .first()
            )
            now = datetime.utcnow()
            if row:
                row.achievements = achievements
                row.comments = comments
                row.updated_at = now
                self.db.commit()
                self.db.refresh(row)
                return {"status": "success", "message": "Registro actualizado.", "id": row.id, "data": _row_to_dict(row)}
            row = CourseLearningAchievementModel(
                course_id=course_id,
                student_id=student_id,
                period_id=period_id,
                achievements=achievements,
                comments=comments,
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro creado.", "id": row.id, "data": _row_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza un registro por id (achievements, comments)."""
        try:
            row = self.db.query(CourseLearningAchievementModel).filter(CourseLearningAchievementModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            if "achievements" in data:
                row.achievements = (data["achievements"] or "").strip() or None
            if "comments" in data:
                row.comments = (data["comments"] or "").strip() or None
            row.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro actualizado.", "id": id, "data": _row_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}

    def delete(self, id: int) -> Any:
        """Elimina un registro por id."""
        try:
            row = self.db.query(CourseLearningAchievementModel).filter(CourseLearningAchievementModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            self.db.delete(row)
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
