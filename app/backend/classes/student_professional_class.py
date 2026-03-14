"""CRUD para tabla students_professionals (relación estudiante-profesional con horas)."""

from datetime import datetime
from typing import Optional, Any, List

from sqlalchemy.orm import Session
from app.backend.db.models import StudentProfessionalModel


class StudentProfessionalClass:
    def __init__(self, db: Session):
        self.db = db

    def get(
        self,
        student_id: Optional[int] = None,
        professional_id: Optional[int] = None,
        include_deleted: bool = False,
    ) -> dict:
        """Lista registros filtrados por student_id y/o professional_id. Por defecto excluye eliminados (deleted_date IS NOT NULL)."""
        try:
            q = self.db.query(StudentProfessionalModel)
            if student_id is not None:
                q = q.filter(StudentProfessionalModel.student_id == student_id)
            if professional_id is not None:
                q = q.filter(StudentProfessionalModel.professional_id == professional_id)
            if not include_deleted:
                q = q.filter(StudentProfessionalModel.deleted_date.is_(None))
            q = q.order_by(StudentProfessionalModel.id.desc())
            rows = q.all()
            data = [
                {
                    "id": r.id,
                    "student_id": r.student_id,
                    "professional_id": r.professional_id,
                    "career_type_id": getattr(r, "career_type_id", None),
                    "hours": r.hours,
                    "added_date": r.added_date.isoformat() if r.added_date else None,
                    "updated_date": r.updated_date.isoformat() if r.updated_date else None,
                    "deleted_date": r.deleted_date.isoformat() if r.deleted_date else None,
                }
                for r in rows
            ]
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_student_and_career_type(self, student_id: int, career_type_id: int) -> dict:
        """Lista registros por student_id y career_type_id, solo sin deleted_date (activos)."""
        try:
            q = (
                self.db.query(StudentProfessionalModel)
                .filter(
                    StudentProfessionalModel.student_id == student_id,
                    StudentProfessionalModel.career_type_id == career_type_id,
                    StudentProfessionalModel.deleted_date.is_(None),
                )
                .order_by(StudentProfessionalModel.id.desc())
            )
            rows = q.all()
            data = [
                {
                    "id": r.id,
                    "student_id": r.student_id,
                    "professional_id": r.professional_id,
                    "career_type_id": getattr(r, "career_type_id", None),
                    "hours": r.hours,
                    "added_date": r.added_date.isoformat() if r.added_date else None,
                    "updated_date": r.updated_date.isoformat() if r.updated_date else None,
                }
                for r in rows
            ]
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> dict:
        """Obtiene un registro por id."""
        try:
            row = self.db.query(StudentProfessionalModel).filter(StudentProfessionalModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            data = {
                "id": row.id,
                "student_id": row.student_id,
                "professional_id": row.professional_id,
                "career_type_id": getattr(row, "career_type_id", None),
                "hours": row.hours,
                "added_date": row.added_date.isoformat() if row.added_date else None,
                "updated_date": row.updated_date.isoformat() if row.updated_date else None,
                "deleted_date": row.deleted_date.isoformat() if row.deleted_date else None,
            }
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> dict:
        """Crea un registro en students_professionals."""
        try:
            row = StudentProfessionalModel(
                student_id=data["student_id"],
                professional_id=data["professional_id"],
                career_type_id=data.get("career_type_id"),
                hours=data.get("hours"),
                added_date=datetime.utcnow(),
                updated_date=datetime.utcnow(),
                deleted_date=None,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro creado.", "id": row.id, "data": {"id": row.id}}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}

    def update(self, id: int, data: dict) -> dict:
        """Actualiza un registro por id (solo campos enviados)."""
        try:
            row = self.db.query(StudentProfessionalModel).filter(StudentProfessionalModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if data.get("student_id") is not None:
                row.student_id = data["student_id"]
            if data.get("professional_id") is not None:
                row.professional_id = data["professional_id"]
            if "career_type_id" in data:
                row.career_type_id = data["career_type_id"]
            if "hours" in data:
                row.hours = data["hours"]
            row.updated_date = datetime.utcnow()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro actualizado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int, soft: bool = True) -> dict:
        """Elimina por id. Si soft=True (por defecto), hace soft delete (deleted_date = now)."""
        try:
            row = self.db.query(StudentProfessionalModel).filter(StudentProfessionalModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if soft:
                row.deleted_date = datetime.utcnow()
                row.updated_date = datetime.utcnow()
                self.db.commit()
                return {"status": "success", "message": "Registro eliminado (soft)."}
            self.db.delete(row)
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
