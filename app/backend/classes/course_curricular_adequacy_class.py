"""Lógica de adecuaciones curriculares por curso: tipos, course_curricular_adequacies, subjects y students."""

from datetime import datetime
from typing import Optional, Any, List
from sqlalchemy.orm import Session
from app.backend.db.models import (
    CurricularAdequacyTypeModel,
    CourseCurricularAdequacyModel,
    CourseCurricularAdequacySubjectModel,
    CourseCurricularAdequacyStudentModel,
)


def _serialize_date(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v) if v else None


def _adequacy_to_dict(r: CourseCurricularAdequacyModel) -> dict:
    return {
        "id": r.id,
        "course_id": r.course_id,
        "curricular_adequacy_type_id": r.curricular_adequacy_type_id,
        "applied": r.applied,
        "scope_text": r.scope_text,
        "strategies_text": r.strategies_text,
        "added_date": _serialize_date(r.added_date),
        "updated_date": _serialize_date(r.updated_date),
        "deleted_date": _serialize_date(r.deleted_date),
    }


class CourseCurricularAdequacyClass:
    def __init__(self, db: Session):
        self.db = db

    def get_types(self) -> Any:
        """Lista tipos de adecuación curricular activos (deleted_date is None), ordenados por sort_order."""
        try:
            rows = (
                self.db.query(CurricularAdequacyTypeModel)
                .filter(CurricularAdequacyTypeModel.deleted_date.is_(None))
                .order_by(CurricularAdequacyTypeModel.sort_order)
                .all()
            )
            return {
                "status": "success",
                "data": [
                    {"id": r.id, "key": r.key, "label": r.label, "sort_order": r.sort_order}
                    for r in rows
                ],
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_course_id(self, course_id: int) -> Any:
        """Estructura completa para el curso: cada tipo con su fila (applied, scope_text, strategies_text, subject_ids, student_ids)."""
        try:
            types_rows = (
                self.db.query(CurricularAdequacyTypeModel)
                .filter(CurricularAdequacyTypeModel.deleted_date.is_(None))
                .order_by(CurricularAdequacyTypeModel.sort_order)
                .all()
            )
            adequacies = (
                self.db.query(CourseCurricularAdequacyModel)
                .filter(
                    CourseCurricularAdequacyModel.course_id == course_id,
                    CourseCurricularAdequacyModel.deleted_date.is_(None),
                )
                .all()
            )
            adj_by_type = {a.curricular_adequacy_type_id: a for a in adequacies}
            result = []
            for t in types_rows:
                adj = adj_by_type.get(t.id)
                subject_ids = []
                student_ids = []
                if adj:
                    subject_ids = [
                        s[0]
                        for s in self.db.query(CourseCurricularAdequacySubjectModel.subject_id)
                        .filter(CourseCurricularAdequacySubjectModel.course_curricular_adequacy_id == adj.id)
                        .all()
                    ]
                    student_ids = [
                        s[0]
                        for s in self.db.query(CourseCurricularAdequacyStudentModel.student_id)
                        .filter(CourseCurricularAdequacyStudentModel.course_curricular_adequacy_id == adj.id)
                        .all()
                    ]
                result.append({
                    "type": {"id": t.id, "key": t.key, "label": t.label, "sort_order": t.sort_order},
                    "adequacy": _adequacy_to_dict(adj) if adj else None,
                    "applied": adj.applied if adj else 0,
                    "scope_text": adj.scope_text if adj else None,
                    "strategies_text": adj.strategies_text if adj else None,
                    "subject_ids": subject_ids,
                    "student_ids": student_ids,
                })
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene una adecuación por id con subject_ids y student_ids."""
        try:
            row = (
                self.db.query(CourseCurricularAdequacyModel)
                .filter(CourseCurricularAdequacyModel.id == id)
                .first()
            )
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            data = _adequacy_to_dict(row)
            data["subject_ids"] = [
                s[0]
                for s in self.db.query(CourseCurricularAdequacySubjectModel.subject_id)
                .filter(CourseCurricularAdequacySubjectModel.course_curricular_adequacy_id == id)
                .all()
            ]
            data["student_ids"] = [
                s[0]
                for s in self.db.query(CourseCurricularAdequacyStudentModel.student_id)
                .filter(CourseCurricularAdequacyStudentModel.course_curricular_adequacy_id == id)
                .all()
            ]
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        """Crea o actualiza una adecuación por (course_id, curricular_adequacy_type_id). Sincroniza subject_ids y student_ids."""
        try:
            course_id = data.get("course_id")
            curricular_adequacy_type_id = data.get("curricular_adequacy_type_id")
            if course_id is None or curricular_adequacy_type_id is None:
                return {"status": "error", "message": "course_id y curricular_adequacy_type_id son requeridos."}
            course_id = int(course_id)
            curricular_adequacy_type_id = int(curricular_adequacy_type_id)
            applied_val = data.get("applied")
            applied = 1 if applied_val in (True, 1, "1") else 0
            scope_text = (data.get("scope_text") or "").strip() or None
            strategies_text = (data.get("strategies_text") or "").strip() or None
            subject_ids = data.get("subject_ids") or []
            student_ids = data.get("student_ids") or []
            now = datetime.now()

            row = (
                self.db.query(CourseCurricularAdequacyModel)
                .filter(
                    CourseCurricularAdequacyModel.course_id == course_id,
                    CourseCurricularAdequacyModel.curricular_adequacy_type_id == curricular_adequacy_type_id,
                )
                .first()
            )
            if row:
                row.applied = applied
                row.scope_text = scope_text
                row.strategies_text = strategies_text
                row.updated_date = now
                row.deleted_date = None
                self.db.commit()
                self.db.refresh(row)
                response_id = row.id
                msg = "Adecuación actualizada."
            else:
                row = CourseCurricularAdequacyModel(
                    course_id=course_id,
                    curricular_adequacy_type_id=curricular_adequacy_type_id,
                    applied=applied,
                    scope_text=scope_text,
                    strategies_text=strategies_text,
                    added_date=now,
                    updated_date=now,
                    deleted_date=None,
                )
                self.db.add(row)
                self.db.commit()
                self.db.refresh(row)
                response_id = row.id
                msg = "Adecuación creada."

            self._sync_subjects(response_id, subject_ids)
            self._sync_students(response_id, student_ids)
            self.db.commit()
            return {"status": "success", "message": msg, "id": response_id, "data": _adequacy_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza una adecuación por id. Opcional: applied, scope_text, strategies_text, subject_ids, student_ids."""
        try:
            row = self.db.query(CourseCurricularAdequacyModel).filter(CourseCurricularAdequacyModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "applied" in data:
                row.applied = 1 if data["applied"] in (True, 1, "1") else 0
            if "scope_text" in data:
                row.scope_text = (data["scope_text"] or "").strip() or None
            if "strategies_text" in data:
                row.strategies_text = (data["strategies_text"] or "").strip() or None
            row.updated_date = datetime.now()
            self.db.commit()
            if "subject_ids" in data:
                self._sync_subjects(id, data["subject_ids"] or [])
            if "student_ids" in data:
                self._sync_students(id, data["student_ids"] or [])
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro actualizado.", "id": id, "data": _adequacy_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        """Borrado lógico (deleted_date)."""
        try:
            row = self.db.query(CourseCurricularAdequacyModel).filter(CourseCurricularAdequacyModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = row.deleted_date
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado.", "id": id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def _sync_subjects(self, course_curricular_adequacy_id: int, subject_ids: List[int]) -> None:
        self.db.query(CourseCurricularAdequacySubjectModel).filter(
            CourseCurricularAdequacySubjectModel.course_curricular_adequacy_id == course_curricular_adequacy_id,
        ).delete(synchronize_session=False)
        now = datetime.now()
        for sid in subject_ids:
            if not sid:
                continue
            self.db.add(CourseCurricularAdequacySubjectModel(
                course_curricular_adequacy_id=course_curricular_adequacy_id,
                subject_id=int(sid),
                added_date=now,
            ))

    def _sync_students(self, course_curricular_adequacy_id: int, student_ids: List[int]) -> None:
        self.db.query(CourseCurricularAdequacyStudentModel).filter(
            CourseCurricularAdequacyStudentModel.course_curricular_adequacy_id == course_curricular_adequacy_id,
        ).delete(synchronize_session=False)
        now = datetime.now()
        for sid in student_ids:
            if not sid:
                continue
            self.db.add(CourseCurricularAdequacyStudentModel(
                course_curricular_adequacy_id=course_curricular_adequacy_id,
                student_id=int(sid),
                added_date=now,
            ))
