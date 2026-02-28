from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.backend.db.models import CollaborativeWorkModel


def _serialize_date(v):
    """Acepta datetime o str (p. ej. si en BD added_date es varchar)."""
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v) if v else None


def _row_to_dict(r: CollaborativeWorkModel) -> dict:
    return {
        "id": r.id,
        "school_id": r.school_id,
        "course_id": r.course_id,
        "planning_collab_co_teaching": r.planning_collab_co_teaching,
        "planning_collab_assistants": r.planning_collab_assistants,
        "planning_collab_students": r.planning_collab_students,
        "planning_collab_family": r.planning_collab_family,
        "planning_collab_community": r.planning_collab_community,
        "planning_observations": r.planning_observations,
        "added_date": _serialize_date(r.added_date),
        "updated_date": _serialize_date(r.updated_date),
        "deleted_date": _serialize_date(r.deleted_date),
    }


class CollaborativeWorkClass:
    def __init__(self, db: Session):
        self.db = db

    def get(
        self,
        school_id: Optional[int] = None,
        course_id: Optional[int] = None,
    ) -> Any:
        """Lista registros activos (deleted_date is None). Filtros opcionales por school_id y course_id (-1 o None = no filtrar)."""
        try:
            q = (
                self.db.query(CollaborativeWorkModel)
                .filter(CollaborativeWorkModel.deleted_date.is_(None))
            )
            if school_id is not None and school_id != -1:
                q = q.filter(CollaborativeWorkModel.school_id == school_id)
            if course_id is not None and course_id != -1:
                q = q.filter(CollaborativeWorkModel.course_id == course_id)
            rows = q.all()
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene un registro por id."""
        try:
            row = self.db.query(CollaborativeWorkModel).filter(CollaborativeWorkModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def get_by_course_id(self, course_id: int) -> Any:
        """Obtiene el registro por course_id. Si ya existe uno para ese curso → UPDATE en store."""
        try:
            row = (
                self.db.query(CollaborativeWorkModel)
                .filter(
                    CollaborativeWorkModel.course_id == course_id,
                    CollaborativeWorkModel.deleted_date.is_(None),
                )
                .first()
            )
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        """Si ya existe un registro activo con el mismo course_id → UPDATE; si no existe → INSERT."""
        try:
            now = datetime.now()
            course_id = data.get("course_id")
            row = (
                self.db.query(CollaborativeWorkModel)
                .filter(
                    CollaborativeWorkModel.course_id == course_id,
                    CollaborativeWorkModel.deleted_date.is_(None),
                )
                .first()
            )
            if row:
                row.school_id = data.get("school_id")
                row.planning_collab_co_teaching = data.get("planning_collab_co_teaching")
                row.planning_collab_assistants = data.get("planning_collab_assistants")
                row.planning_collab_students = data.get("planning_collab_students")
                row.planning_collab_family = data.get("planning_collab_family")
                row.planning_collab_community = data.get("planning_collab_community")
                row.planning_observations = data.get("planning_observations")
                row.updated_date = now
                self.db.commit()
                self.db.refresh(row)
                return {"status": "success", "message": "Registro actualizado.", "id": row.id, "data": _row_to_dict(row)}
            row = CollaborativeWorkModel(
                school_id=data.get("school_id"),
                course_id=course_id,
                planning_collab_co_teaching=data.get("planning_collab_co_teaching"),
                planning_collab_assistants=data.get("planning_collab_assistants"),
                planning_collab_students=data.get("planning_collab_students"),
                planning_collab_family=data.get("planning_collab_family"),
                planning_collab_community=data.get("planning_collab_community"),
                planning_observations=data.get("planning_observations"),
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
            row = self.db.query(CollaborativeWorkModel).filter(CollaborativeWorkModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            for key in ("school_id", "course_id", "planning_collab_co_teaching", "planning_collab_assistants",
                        "planning_collab_students", "planning_collab_family", "planning_collab_community", "planning_observations"):
                if key in data:
                    setattr(row, key, data[key])
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
            row = self.db.query(CollaborativeWorkModel).filter(CollaborativeWorkModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = datetime.now()
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
