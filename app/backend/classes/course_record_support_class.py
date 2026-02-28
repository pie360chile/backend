"""Card 2: Registro de apoyos por curso y área (objetivos, estudiantes, intervenciones)."""

from datetime import datetime, date
from typing import Optional, Any, List
from sqlalchemy.orm import Session
from app.backend.db.models import (
    CourseRecordSupportModel,
    CourseRecordSupportStudentModel,
    CourseRecordSupportInterventionModel,
    SupportAreaModel,
    ProfessionalModel,
)


def _serialize_date(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v) if v else None


def _parse_date(s: Optional[str]) -> Optional[date]:
    if s is None or (isinstance(s, str) and not s.strip()):
        return None
    if isinstance(s, date):
        return s
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _intervention_to_dict(row: CourseRecordSupportInterventionModel, professional_name: Optional[str] = None) -> dict:
    return {
        "id": row.id,
        "course_id": row.course_id,
        "support_area_id": row.support_area_id,
        "date": _serialize_date(row.date),
        "pedagogicalHours": float(row.pedagogical_hours) if row.pedagogical_hours is not None else None,
        "place": row.place,
        "professionalId": row.professional_id,
        "professionalName": professional_name,
        "activitiesDescription": row.activities_description,
        "created_at": _serialize_date(row.created_at),
        "updated_at": _serialize_date(row.updated_at),
    }


class CourseRecordSupportClass:
    def __init__(self, db: Session):
        self.db = db

    def get_by_course_id(self, course_id: int) -> Any:
        """Lista por curso: todas las áreas con su registro (objetivos, student_ids, interventions)."""
        try:
            areas = self.db.query(SupportAreaModel).order_by(SupportAreaModel.support_area.asc()).all()
            records = (
                self.db.query(CourseRecordSupportModel)
                .filter(CourseRecordSupportModel.course_id == course_id)
                .all()
            )
            record_by_area = {r.support_area_id: r for r in records}
            result = []
            for area in areas:
                rec = record_by_area.get(area.id)
                learning_objectives = rec.learning_objectives if rec else None
                record_id = rec.id if rec else None
                student_ids = []
                if record_id:
                    student_ids = [
                        s[0]
                        for s in self.db.query(CourseRecordSupportStudentModel.student_id)
                        .filter(CourseRecordSupportStudentModel.course_record_support_id == record_id)
                        .all()
                    ]
                interventions_rows = (
                    self.db.query(CourseRecordSupportInterventionModel)
                    .filter(
                        CourseRecordSupportInterventionModel.course_id == course_id,
                        CourseRecordSupportInterventionModel.support_area_id == area.id,
                    )
                    .order_by(CourseRecordSupportInterventionModel.date.desc(), CourseRecordSupportInterventionModel.id.desc())
                    .all()
                )
                professional_ids = [r.professional_id for r in interventions_rows if r.professional_id is not None]
                prof_names = {}
                if professional_ids:
                    for p in self.db.query(ProfessionalModel).filter(ProfessionalModel.id.in_(professional_ids)).all():
                        name = getattr(p, "names", None) and getattr(p, "lastnames", None)
                        if name:
                            prof_names[p.id] = f"{p.names} {p.lastnames}".strip()
                        else:
                            prof_names[p.id] = getattr(p, "name", None) or str(p.id)
                interventions = [
                    _intervention_to_dict(r, professional_name=prof_names.get(r.professional_id))
                    for r in interventions_rows
                ]
                result.append({
                    "support_area_id": area.id,
                    "support_area": area.support_area or "",
                    "learning_objectives": learning_objectives,
                    "student_ids": student_ids,
                    "interventions": interventions,
                })
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def save_record(self, data: dict) -> Any:
        """Crea o actualiza course_record_support (objetivos) y sincroniza student_ids."""
        try:
            course_id = int(data.get("course_id"))
            support_area_id = int(data.get("support_area_id"))
            learning_objectives = (data.get("learning_objectives") or "").strip() or None
            student_ids = data.get("student_ids") or []

            rec = (
                self.db.query(CourseRecordSupportModel)
                .filter(
                    CourseRecordSupportModel.course_id == course_id,
                    CourseRecordSupportModel.support_area_id == support_area_id,
                )
                .first()
            )
            if rec:
                rec.learning_objectives = learning_objectives
                rec.updated_at = datetime.utcnow()
                self.db.flush()
                record_id = rec.id
            else:
                rec = CourseRecordSupportModel(
                    course_id=course_id,
                    support_area_id=support_area_id,
                    learning_objectives=learning_objectives,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                self.db.add(rec)
                self.db.flush()
                record_id = rec.id

            self.db.query(CourseRecordSupportStudentModel).filter(
                CourseRecordSupportStudentModel.course_record_support_id == record_id,
            ).delete(synchronize_session=False)
            for sid in student_ids:
                if sid is None:
                    continue
                self.db.add(CourseRecordSupportStudentModel(
                    course_record_support_id=record_id,
                    student_id=int(sid),
                    created_at=datetime.utcnow(),
                ))
            self.db.commit()
            return {"status": "success", "message": "Datos guardados.", "id": record_id, "data": {"id": record_id}}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}

    def get_interventions(self, course_id: int, support_area_id: int) -> Any:
        """Lista intervenciones por curso y área."""
        try:
            rows = (
                self.db.query(CourseRecordSupportInterventionModel)
                .filter(
                    CourseRecordSupportInterventionModel.course_id == course_id,
                    CourseRecordSupportInterventionModel.support_area_id == support_area_id,
                )
                .order_by(CourseRecordSupportInterventionModel.date.desc(), CourseRecordSupportInterventionModel.id.desc())
                .all()
            )
            professional_ids = [r.professional_id for r in rows if r.professional_id is not None]
            prof_names = {}
            if professional_ids:
                for p in self.db.query(ProfessionalModel).filter(ProfessionalModel.id.in_(professional_ids)).all():
                    name = getattr(p, "names", None) and getattr(p, "lastnames", None)
                    if name:
                        prof_names[p.id] = f"{p.names} {p.lastnames}".strip()
                    else:
                        prof_names[p.id] = getattr(p, "name", None) or str(p.id)
            data = [_intervention_to_dict(r, professional_name=prof_names.get(r.professional_id)) for r in rows]
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_intervention_by_id(self, id: int) -> Any:
        """Obtiene una intervención por id."""
        try:
            row = self.db.query(CourseRecordSupportInterventionModel).filter(CourseRecordSupportInterventionModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Intervención no encontrada.", "data": None}
            prof_name = None
            if row.professional_id:
                p = self.db.query(ProfessionalModel).filter(ProfessionalModel.id == row.professional_id).first()
                if p:
                    prof_name = (getattr(p, "names", "") or "") + " " + (getattr(p, "lastnames", "") or "")
                    prof_name = prof_name.strip() or getattr(p, "name", None)
            data = _intervention_to_dict(row, professional_name=prof_name)
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store_intervention(self, data: dict) -> Any:
        """Crea una intervención (Ingresar apoyo)."""
        try:
            course_id = int(data.get("course_id"))
            support_area_id = int(data.get("support_area_id"))
            dt = _parse_date(data.get("date"))
            if not dt:
                return {"status": "error", "message": "Indique la fecha.", "data": None}
            pedagogical_hours = data.get("pedagogical_hours")
            if pedagogical_hours is not None:
                pedagogical_hours = float(pedagogical_hours)
            place = (data.get("place") or "").strip() or None
            professional_id = data.get("professional_id")
            professional_id = int(professional_id) if professional_id is not None else None
            activities_description = (data.get("activities_description") or "").strip() or None

            row = CourseRecordSupportInterventionModel(
                course_id=course_id,
                support_area_id=support_area_id,
                date=dt,
                pedagogical_hours=pedagogical_hours,
                place=place,
                professional_id=professional_id,
                activities_description=activities_description,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            prof_name = None
            if row.professional_id:
                p = self.db.query(ProfessionalModel).filter(ProfessionalModel.id == row.professional_id).first()
                if p:
                    prof_name = (getattr(p, "names", "") or "") + " " + (getattr(p, "lastnames", "") or "")
                    prof_name = prof_name.strip()
            out = _intervention_to_dict(row, professional_name=prof_name)
            return {"status": "success", "message": "Apoyo registrado.", "id": row.id, "data": out}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}

    def update_intervention(self, id: int, data: dict) -> Any:
        """Actualiza una intervención por id."""
        try:
            row = self.db.query(CourseRecordSupportInterventionModel).filter(CourseRecordSupportInterventionModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Intervención no encontrada.", "data": None}
            if "date" in data and data["date"]:
                dt = _parse_date(data["date"])
                if dt:
                    row.date = dt
            if "pedagogical_hours" in data:
                row.pedagogical_hours = float(data["pedagogical_hours"]) if data["pedagogical_hours"] is not None else None
            if "place" in data:
                row.place = (data["place"] or "").strip() or None
            if "professional_id" in data:
                row.professional_id = int(data["professional_id"]) if data["professional_id"] is not None else None
            if "activities_description" in data:
                row.activities_description = (data["activities_description"] or "").strip() or None
            row.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(row)
            prof_name = None
            if row.professional_id:
                p = self.db.query(ProfessionalModel).filter(ProfessionalModel.id == row.professional_id).first()
                if p:
                    prof_name = (getattr(p, "names", "") or "") + " " + (getattr(p, "lastnames", "") or "")
                    prof_name = prof_name.strip()
            out = _intervention_to_dict(row, professional_name=prof_name)
            return {"status": "success", "message": "Intervención actualizada.", "id": id, "data": out}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}

    def delete_intervention(self, id: int) -> Any:
        """Elimina una intervención por id."""
        try:
            row = self.db.query(CourseRecordSupportInterventionModel).filter(CourseRecordSupportInterventionModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Intervención no encontrada."}
            self.db.delete(row)
            self.db.commit()
            return {"status": "success", "message": "Intervención eliminada."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
