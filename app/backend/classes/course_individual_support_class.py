"""Lógica de Plan de Apoyo Individual por curso: course_individual_supports y students."""

from datetime import datetime, date
from typing import Optional, Any, List
from sqlalchemy.orm import Session
from app.backend.db.models import (
    CourseIndividualSupportModel,
    CourseIndividualSupportStudentModel,
    SupportAreaModel,
)


def _serialize_date(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v) if v else None


def _support_to_dict(r: CourseIndividualSupportModel, support_area_name: Optional[str] = None) -> dict:
    d = {
        "id": r.id,
        "course_id": r.course_id,
        "support_area_id": r.support_area_id,
        "support_area_name": support_area_name,
        "horario": r.horario,
        "fecha_inicio": _serialize_date(r.fecha_inicio),
        "fecha_termino": _serialize_date(r.fecha_termino),
        "added_date": _serialize_date(r.added_date),
        "updated_date": _serialize_date(r.updated_date),
        "deleted_date": _serialize_date(r.deleted_date),
    }
    return d


def _get_support_area_name(db: Session, support_area_id: Optional[int]) -> Optional[str]:
    if support_area_id is None:
        return None
    row = db.query(SupportAreaModel).filter(SupportAreaModel.id == support_area_id).first()
    return row.support_area if row else None


def _parse_date(s: Optional[str]) -> Optional[date]:
    if s is None or (isinstance(s, str) and not s.strip()):
        return None
    if isinstance(s, date):
        return s
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


class CourseIndividualSupportClass:
    def __init__(self, db: Session):
        self.db = db

    def get_by_course_id(self, course_id: int, include_deleted: bool = False) -> Any:
        """Lista apoyos individuales del curso (cada uno con student_ids)."""
        try:
            q = self.db.query(CourseIndividualSupportModel).filter(
                CourseIndividualSupportModel.course_id == course_id,
            )
            if not include_deleted:
                q = q.filter(CourseIndividualSupportModel.deleted_date.is_(None))
            rows = q.order_by(CourseIndividualSupportModel.added_date.desc()).all()
            support_area_ids = [r.support_area_id for r in rows if r.support_area_id is not None]
            name_by_id = {}
            if support_area_ids:
                for area in self.db.query(SupportAreaModel).filter(SupportAreaModel.id.in_(support_area_ids)).all():
                    name_by_id[area.id] = area.support_area
            result = []
            for r in rows:
                item = _support_to_dict(r, support_area_name=name_by_id.get(r.support_area_id))
                item["student_ids"] = [
                    s[0]
                    for s in self.db.query(CourseIndividualSupportStudentModel.student_id)
                    .filter(CourseIndividualSupportStudentModel.course_individual_support_id == r.id)
                    .all()
                ]
                result.append(item)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene un apoyo individual por id con student_ids."""
        try:
            row = (
                self.db.query(CourseIndividualSupportModel)
                .filter(CourseIndividualSupportModel.id == id)
                .first()
            )
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            data = _support_to_dict(row, support_area_name=_get_support_area_name(self.db, row.support_area_id))
            data["student_ids"] = [
                s[0]
                for s in self.db.query(CourseIndividualSupportStudentModel.student_id)
                .filter(CourseIndividualSupportStudentModel.course_individual_support_id == id)
                .all()
            ]
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        """Crea un apoyo individual (course_id, support_area_id, horario, fecha_inicio, fecha_termino, student_ids)."""
        try:
            course_id = data.get("course_id")
            if course_id is None:
                return {"status": "error", "message": "course_id es requerido."}
            course_id = int(course_id)
            support_area_id = data.get("support_area_id")
            support_area_id = int(support_area_id) if support_area_id is not None else None
            horario = (data.get("horario") or "").strip() or None
            fecha_inicio = _parse_date(data.get("fecha_inicio"))
            fecha_termino = _parse_date(data.get("fecha_termino"))
            student_ids = data.get("student_ids") or []
            now = datetime.now()

            row = CourseIndividualSupportModel(
                course_id=course_id,
                support_area_id=support_area_id,
                horario=horario,
                fecha_inicio=fecha_inicio,
                fecha_termino=fecha_termino,
                added_date=now,
                updated_date=now,
                deleted_date=None,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            response_id = row.id
            self._sync_students(response_id, student_ids)
            self.db.commit()
            return {"status": "success", "message": "Apoyo individual creado.", "id": response_id, "data": _support_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza un apoyo individual por id. Opcional: support_area_id, horario, fecha_inicio, fecha_termino, student_ids."""
        try:
            row = self.db.query(CourseIndividualSupportModel).filter(CourseIndividualSupportModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "support_area_id" in data:
                row.support_area_id = int(data["support_area_id"]) if data["support_area_id"] is not None else None
            if "horario" in data:
                row.horario = (data["horario"] or "").strip() or None
            if "fecha_inicio" in data:
                row.fecha_inicio = _parse_date(data["fecha_inicio"])
            if "fecha_termino" in data:
                row.fecha_termino = _parse_date(data["fecha_termino"])
            row.updated_date = datetime.now()
            self.db.commit()
            if "student_ids" in data:
                self._sync_students(id, data["student_ids"] or [])
                self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro actualizado.", "id": id, "data": _support_to_dict(row, support_area_name=_get_support_area_name(self.db, row.support_area_id))}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        """Borrado lógico (deleted_date)."""
        try:
            row = self.db.query(CourseIndividualSupportModel).filter(CourseIndividualSupportModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = row.deleted_date
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado.", "id": id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def _sync_students(self, course_individual_support_id: int, student_ids: List[int]) -> None:
        self.db.query(CourseIndividualSupportStudentModel).filter(
            CourseIndividualSupportStudentModel.course_individual_support_id == course_individual_support_id,
        ).delete(synchronize_session=False)
        now = datetime.now()
        for sid in student_ids:
            if not sid:
                continue
            self.db.add(CourseIndividualSupportStudentModel(
                course_individual_support_id=course_individual_support_id,
                student_id=int(sid),
                added_date=now,
            ))
