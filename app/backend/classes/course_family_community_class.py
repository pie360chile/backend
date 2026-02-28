"""Logic for 5. Estrategias de trabajo con la familia y con la comunidad."""

from datetime import datetime
from typing import Optional, Any, List
from sqlalchemy.orm import Session
from app.backend.db.models import (
    FamilyCommunityStrategyTypeModel,
    CourseFamilyCommunityModel,
    CourseFamilyCommunityObservationModel,
)


def _serialize_date(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v) if v else None


def _row_to_dict(r: CourseFamilyCommunityModel) -> dict:
    return {
        "id": r.id,
        "course_id": r.course_id,
        "family_community_strategy_type_id": r.family_community_strategy_type_id,
        "descripcion": r.descripcion,
        "seguimiento": r.seguimiento,
        "evaluacion": r.evaluacion,
        "added_date": _serialize_date(r.added_date),
        "updated_date": _serialize_date(r.updated_date),
        "deleted_date": _serialize_date(r.deleted_date),
    }


class CourseFamilyCommunityClass:
    def __init__(self, db: Session):
        self.db = db

    def get_types(self) -> Any:
        """List strategy types (deleted_date is None), ordered by sort_order."""
        try:
            rows = (
                self.db.query(FamilyCommunityStrategyTypeModel)
                .filter(FamilyCommunityStrategyTypeModel.deleted_date.is_(None))
                .order_by(FamilyCommunityStrategyTypeModel.sort_order)
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
        """Full structure for the course: each type with descripcion, seguimiento, evaluacion and observations."""
        try:
            types_rows = (
                self.db.query(FamilyCommunityStrategyTypeModel)
                .filter(FamilyCommunityStrategyTypeModel.deleted_date.is_(None))
                .order_by(FamilyCommunityStrategyTypeModel.sort_order)
                .all()
            )
            rows = (
                self.db.query(CourseFamilyCommunityModel)
                .filter(
                    CourseFamilyCommunityModel.course_id == course_id,
                    CourseFamilyCommunityModel.deleted_date.is_(None),
                )
                .all()
            )
            row_by_type = {r.family_community_strategy_type_id: r for r in rows}
            obs_row = (
                self.db.query(CourseFamilyCommunityObservationModel)
                .filter(
                    CourseFamilyCommunityObservationModel.course_id == course_id,
                    CourseFamilyCommunityObservationModel.deleted_date.is_(None),
                )
                .first()
            )
            observations = obs_row.observations if obs_row else None
            result = []
            for t in types_rows:
                r = row_by_type.get(t.id)
                result.append({
                    "type": {"id": t.id, "key": t.key, "label": t.label, "sort_order": t.sort_order},
                    "row": _row_to_dict(r) if r else None,
                    "descripcion": r.descripcion if r else None,
                    "seguimiento": r.seguimiento if r else None,
                    "evaluacion": r.evaluacion if r else None,
                })
            return {"status": "success", "data": result, "observations": observations}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": [], "observations": None}

    def get_by_id(self, id: int) -> Any:
        """Get one course_family_community by id."""
        try:
            row = (
                self.db.query(CourseFamilyCommunityModel)
                .filter(CourseFamilyCommunityModel.id == id)
                .first()
            )
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def get_observations(self, course_id: int) -> Any:
        """Get observations for section 5 (one per course)."""
        try:
            row = (
                self.db.query(CourseFamilyCommunityObservationModel)
                .filter(
                    CourseFamilyCommunityObservationModel.course_id == course_id,
                    CourseFamilyCommunityObservationModel.deleted_date.is_(None),
                )
                .first()
            )
            return {"status": "success", "data": {"observations": row.observations if row else None}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def set_observations(self, course_id: int, observations: Optional[str]) -> Any:
        """Create or update observations for the course (one row per course_id)."""
        try:
            row = (
                self.db.query(CourseFamilyCommunityObservationModel)
                .filter(CourseFamilyCommunityObservationModel.course_id == course_id)
                .first()
            )
            now = datetime.now()
            text = (observations or "").strip() if observations is not None else ""
            if row:
                row.observations = text or None
                row.updated_date = now
                row.deleted_date = None
            else:
                self.db.add(CourseFamilyCommunityObservationModel(
                    course_id=course_id,
                    observations=text or None,
                    added_date=now,
                    updated_date=now,
                    deleted_date=None,
                ))
            self.db.commit()
            return {"status": "success", "message": "Observaciones guardadas."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def store(self, data: dict) -> Any:
        """Create or update one row by (course_id, family_community_strategy_type_id). Optionally save observations."""
        try:
            course_id = data.get("course_id")
            family_community_strategy_type_id = data.get("family_community_strategy_type_id")
            if course_id is None or family_community_strategy_type_id is None:
                return {"status": "error", "message": "course_id y family_community_strategy_type_id son requeridos."}
            course_id = int(course_id)
            family_community_strategy_type_id = int(family_community_strategy_type_id)
            descripcion = (data.get("descripcion") or "").strip() or None
            seguimiento = (data.get("seguimiento") or "").strip() or None
            evaluacion = (data.get("evaluacion") or "").strip() or None
            now = datetime.now()

            row = (
                self.db.query(CourseFamilyCommunityModel)
                .filter(
                    CourseFamilyCommunityModel.course_id == course_id,
                    CourseFamilyCommunityModel.family_community_strategy_type_id == family_community_strategy_type_id,
                )
                .first()
            )
            if row:
                row.descripcion = descripcion
                row.seguimiento = seguimiento
                row.evaluacion = evaluacion
                row.updated_date = now
                row.deleted_date = None
                self.db.commit()
                self.db.refresh(row)
                response_id = row.id
                msg = "Registro actualizado."
            else:
                row = CourseFamilyCommunityModel(
                    course_id=course_id,
                    family_community_strategy_type_id=family_community_strategy_type_id,
                    descripcion=descripcion,
                    seguimiento=seguimiento,
                    evaluacion=evaluacion,
                    added_date=now,
                    updated_date=now,
                    deleted_date=None,
                )
                self.db.add(row)
                self.db.commit()
                self.db.refresh(row)
                response_id = row.id
                msg = "Registro creado."

            if "observations" in data:
                self.set_observations(course_id, data.get("observations"))
            return {"status": "success", "message": msg, "id": response_id, "data": _row_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Update one course_family_community by id (optional: descripcion, seguimiento, evaluacion)."""
        try:
            row = self.db.query(CourseFamilyCommunityModel).filter(CourseFamilyCommunityModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "descripcion" in data:
                row.descripcion = (data["descripcion"] or "").strip() or None
            if "seguimiento" in data:
                row.seguimiento = (data["seguimiento"] or "").strip() or None
            if "evaluacion" in data:
                row.evaluacion = (data["evaluacion"] or "").strip() or None
            row.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro actualizado.", "id": id, "data": _row_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        """Soft delete (deleted_date)."""
        try:
            row = self.db.query(CourseFamilyCommunityModel).filter(CourseFamilyCommunityModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = row.deleted_date
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado.", "id": id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
