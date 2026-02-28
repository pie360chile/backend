"""Lógica de ajustes por curso: adjustment_aspects, course_adjustments, course_adjustment_students."""

from datetime import datetime
from typing import Optional, Any, List
from sqlalchemy.orm import Session
from app.backend.db.models import (
    AdjustmentAspectModel,
    CourseAdjustmentModel,
    CourseAdjustmentStudentModel,
)


def _serialize_date(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v) if v else None


def _adjustment_to_dict(r: CourseAdjustmentModel) -> dict:
    return {
        "id": r.id,
        "course_id": r.course_id,
        "adjustment_aspect_id": r.adjustment_aspect_id,
        "other_aspect_text": r.other_aspect_text,
        "value": r.value,
        "added_date": _serialize_date(r.added_date),
        "updated_date": _serialize_date(r.updated_date),
        "deleted_date": _serialize_date(r.deleted_date),
    }


class CourseAdjustmentClass:
    def __init__(self, db: Session):
        self.db = db

    def get_aspects(self) -> Any:
        """Lista aspectos de ajuste activos (deleted_date is None), ordenados por sort_order."""
        try:
            rows = (
                self.db.query(AdjustmentAspectModel)
                .filter(AdjustmentAspectModel.deleted_date.is_(None))
                .order_by(AdjustmentAspectModel.sort_order)
                .all()
            )
            return {
                "status": "success",
                "data": [
                    {
                        "id": r.id,
                        "key": r.key,
                        "label": r.label,
                        "sort_order": r.sort_order,
                    }
                    for r in rows
                ],
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_course_id(self, course_id: int) -> Any:
        """Estructura completa para el curso: cada aspecto con su fila de ajuste (value, other_aspect_text) y student_ids."""
        try:
            aspects = (
                self.db.query(AdjustmentAspectModel)
                .filter(AdjustmentAspectModel.deleted_date.is_(None))
                .order_by(AdjustmentAspectModel.sort_order)
                .all()
            )
            adjustments = (
                self.db.query(CourseAdjustmentModel)
                .filter(
                    CourseAdjustmentModel.course_id == course_id,
                    CourseAdjustmentModel.deleted_date.is_(None),
                )
                .all()
            )
            adj_by_aspect = {a.adjustment_aspect_id: a for a in adjustments}
            result = []
            for asp in aspects:
                adj = adj_by_aspect.get(asp.id)
                student_ids = []
                if adj:
                    student_ids = [
                        s[0]
                        for s in self.db.query(CourseAdjustmentStudentModel.student_id)
                        .filter(CourseAdjustmentStudentModel.course_adjustment_id == adj.id)
                        .all()
                    ]
                result.append({
                    "aspect": {
                        "id": asp.id,
                        "key": asp.key,
                        "label": asp.label,
                        "sort_order": asp.sort_order,
                    },
                    "adjustment": _adjustment_to_dict(adj) if adj else None,
                    "value": adj.value if adj else None,
                    "other_aspect_text": adj.other_aspect_text if adj else None,
                    "student_ids": student_ids,
                })
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene un course_adjustment por id con student_ids."""
        try:
            row = (
                self.db.query(CourseAdjustmentModel)
                .filter(CourseAdjustmentModel.id == id)
                .first()
            )
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            data = _adjustment_to_dict(row)
            data["student_ids"] = [
                s[0]
                for s in self.db.query(CourseAdjustmentStudentModel.student_id)
                .filter(CourseAdjustmentStudentModel.course_adjustment_id == id)
                .all()
            ]
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        """Crea o actualiza un ajuste por (course_id, adjustment_aspect_id). Sincroniza student_ids."""
        try:
            course_id = data.get("course_id")
            adjustment_aspect_id = data.get("adjustment_aspect_id")
            if course_id is None or adjustment_aspect_id is None:
                return {"status": "error", "message": "course_id y adjustment_aspect_id son requeridos."}
            course_id = int(course_id)
            adjustment_aspect_id = int(adjustment_aspect_id)
            other_aspect_text = data.get("other_aspect_text")
            value = data.get("value")
            student_ids = data.get("student_ids") or []
            now = datetime.now()

            row = (
                self.db.query(CourseAdjustmentModel)
                .filter(
                    CourseAdjustmentModel.course_id == course_id,
                    CourseAdjustmentModel.adjustment_aspect_id == adjustment_aspect_id,
                )
                .first()
            )
            if row:
                row.other_aspect_text = (other_aspect_text or "").strip() or None
                row.value = (value or "").strip() or None
                row.updated_date = now
                row.deleted_date = None
                self.db.commit()
                self.db.refresh(row)
                response_id = row.id
                msg = "Ajuste actualizado."
            else:
                row = CourseAdjustmentModel(
                    course_id=course_id,
                    adjustment_aspect_id=adjustment_aspect_id,
                    other_aspect_text=(other_aspect_text or "").strip() or None,
                    value=(value or "").strip() or None,
                    added_date=now,
                    updated_date=now,
                    deleted_date=None,
                )
                self.db.add(row)
                self.db.commit()
                self.db.refresh(row)
                response_id = row.id
                msg = "Ajuste creado."

            self._sync_students(response_id, student_ids)
            self.db.commit()
            return {"status": "success", "message": msg, "id": response_id, "data": _adjustment_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza un course_adjustment por id. Opcional: other_aspect_text, value, student_ids."""
        try:
            row = self.db.query(CourseAdjustmentModel).filter(CourseAdjustmentModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "other_aspect_text" in data:
                row.other_aspect_text = (data["other_aspect_text"] or "").strip() or None
            if "value" in data:
                row.value = (data["value"] or "").strip() or None
            row.updated_date = datetime.now()
            self.db.commit()
            if "student_ids" in data:
                self._sync_students(id, data["student_ids"] or [])
                self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro actualizado.", "id": id, "data": _adjustment_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        """Borrado lógico del course_adjustment (deleted_date)."""
        try:
            row = self.db.query(CourseAdjustmentModel).filter(CourseAdjustmentModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = row.deleted_date
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado.", "id": id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def _sync_students(self, course_adjustment_id: int, student_ids: List[int]) -> None:
        """Reemplaza los estudiantes asociados al ajuste por student_ids."""
        self.db.query(CourseAdjustmentStudentModel).filter(
            CourseAdjustmentStudentModel.course_adjustment_id == course_adjustment_id,
        ).delete(synchronize_session=False)
        now = datetime.now()
        for sid in student_ids:
            if not sid:
                continue
            self.db.add(CourseAdjustmentStudentModel(
                course_adjustment_id=course_adjustment_id,
                student_id=int(sid),
                added_date=now,
            ))
