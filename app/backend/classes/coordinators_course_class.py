from datetime import datetime
from typing import Optional, Any, List
from app.backend.db.models import CoordinatorsCourseModel


def _row_to_dict(r: CoordinatorsCourseModel) -> dict:
    return {
        "id": r.id,
        "school_id": r.school_id,
        "course_id": r.course_id,
        "professional_id": r.professional_id,
        "coordinator_type_id": r.coordinator_type_id,
        "phone": r.phone,
        "email": r.email,
        "added_date": r.added_date.isoformat() if r.added_date else None,
        "updated_date": r.updated_date.isoformat() if r.updated_date else None,
        "deleted_date": r.deleted_date.isoformat() if r.deleted_date else None,
    }


class CoordinatorsCourseClass:
    def __init__(self, db):
        self.db = db

    def get(
        self,
        school_id: Optional[int] = None,
        course_id: Optional[int] = None,
        professional_id: Optional[int] = None,
        coordinator_type_id: Optional[int] = None,
    ) -> Any:
        """Lista registros activos (deleted_date is None), con filtros opcionales (-1 o None = no filtrar)."""
        try:
            q = (
                self.db.query(CoordinatorsCourseModel)
                .filter(CoordinatorsCourseModel.deleted_date.is_(None))
            )
            if school_id is not None and school_id != -1:
                q = q.filter(CoordinatorsCourseModel.school_id == school_id)
            if course_id is not None and course_id != -1:
                q = q.filter(CoordinatorsCourseModel.course_id == course_id)
            if professional_id is not None and professional_id != -1:
                q = q.filter(CoordinatorsCourseModel.professional_id == professional_id)
            if coordinator_type_id is not None and coordinator_type_id != -1:
                q = q.filter(CoordinatorsCourseModel.coordinator_type_id == coordinator_type_id)
            rows = q.all()
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene un registro por id."""
        try:
            row = self.db.query(CoordinatorsCourseModel).filter(CoordinatorsCourseModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        """Crea un registro en coordinators_courses."""
        try:
            now = datetime.now()
            row = CoordinatorsCourseModel(
                school_id=data.get("school_id"),
                course_id=data.get("course_id"),
                professional_id=data.get("professional_id"),
                coordinator_type_id=data.get("coordinator_type_id"),
                phone=data.get("phone"),
                email=data.get("email"),
                added_date=now,
                updated_date=now,
                deleted_date=None,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro creado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza un registro; solo los campos enviados."""
        try:
            row = self.db.query(CoordinatorsCourseModel).filter(CoordinatorsCourseModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "school_id" in data and data["school_id"] is not None:
                row.school_id = data["school_id"]
            if "course_id" in data and data["course_id"] is not None:
                row.course_id = data["course_id"]
            if "professional_id" in data and data["professional_id"] is not None:
                row.professional_id = data["professional_id"]
            if "coordinator_type_id" in data and data["coordinator_type_id"] is not None:
                row.coordinator_type_id = data["coordinator_type_id"]
            if "phone" in data:
                row.phone = data["phone"]
            if "email" in data:
                row.email = data["email"]
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
            row = self.db.query(CoordinatorsCourseModel).filter(CoordinatorsCourseModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = datetime.now()
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
