from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.backend.db.models import SupportOrganizationModel


def _serialize_date(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v) if v else None


def _row_to_dict(r: SupportOrganizationModel) -> dict:
    return {
        "id": r.id,
        "school_id": r.school_id,
        "course_id": r.course_id,
        "subject_id": r.subject_id,
        "hours_support_regular_classroom": r.hours_support_regular_classroom,
        "hours_support_outside_classroom": r.hours_support_outside_classroom,
        "specialized_support_types": r.specialized_support_types,
        "added_date": _serialize_date(r.added_date),
        "updated_date": _serialize_date(r.updated_date),
        "deleted_date": _serialize_date(r.deleted_date),
    }


class SupportOrganizationClass:
    def __init__(self, db: Session):
        self.db = db

    def get(
        self,
        school_id: Optional[int] = None,
        course_id: Optional[int] = None,
        subject_id: Optional[int] = None,
    ) -> Any:
        """Lista registros activos (deleted_date is None). Filtros opcionales por school_id, course_id, subject_id."""
        try:
            q = (
                self.db.query(SupportOrganizationModel)
                .filter(SupportOrganizationModel.deleted_date.is_(None))
            )
            if school_id is not None and school_id != -1:
                q = q.filter(SupportOrganizationModel.school_id == school_id)
            if course_id is not None and course_id != -1:
                q = q.filter(SupportOrganizationModel.course_id == course_id)
            if subject_id is not None and subject_id != -1:
                q = q.filter(SupportOrganizationModel.subject_id == subject_id)
            rows = q.all()
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene un registro por id."""
        try:
            row = self.db.query(SupportOrganizationModel).filter(SupportOrganizationModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def get_by_course_id(self, course_id: int) -> Any:
        """Obtiene la lista de registros activos para un course_id."""
        try:
            rows = (
                self.db.query(SupportOrganizationModel)
                .filter(
                    SupportOrganizationModel.course_id == course_id,
                    SupportOrganizationModel.deleted_date.is_(None),
                )
                .all()
            )
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def store(self, data: dict) -> Any:
        """Crea un registro en support_organizations. school_id del body o de la sesión."""
        try:
            now = datetime.now()
            row = SupportOrganizationModel(
                school_id=data.get("school_id"),
                course_id=data.get("course_id"),
                subject_id=data.get("subject_id"),
                hours_support_regular_classroom=data.get("hours_support_regular_classroom"),
                hours_support_outside_classroom=data.get("hours_support_outside_classroom"),
                specialized_support_types=data.get("specialized_support_types"),
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
            row = self.db.query(SupportOrganizationModel).filter(SupportOrganizationModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            for key in (
                "school_id", "course_id", "subject_id",
                "hours_support_regular_classroom", "hours_support_outside_classroom", "specialized_support_types",
            ):
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
            row = self.db.query(SupportOrganizationModel).filter(SupportOrganizationModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = datetime.now()
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
