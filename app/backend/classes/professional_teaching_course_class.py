from datetime import datetime
from app.backend.db.models import ProfessionalTeachingCourseModel


class ProfessionalTeachingCourseClass:
    def __init__(self, db):
        self.db = db

    def get(
        self,
        professional_id=None,
        teaching_id=None,
        course_id=None,
        teacher_type_id=None,
        deleted_status_id=None,
    ):
        """Lista asignaciones filtrando por los par?metros indicados (-1 o None = no filtrar)."""
        try:
            q = self.db.query(ProfessionalTeachingCourseModel)
            if professional_id is not None and professional_id != -1:
                q = q.filter(ProfessionalTeachingCourseModel.professional_id == professional_id)
            if teaching_id is not None and teaching_id != -1:
                q = q.filter(ProfessionalTeachingCourseModel.teaching_id == teaching_id)
            if course_id is not None and course_id != -1:
                q = q.filter(ProfessionalTeachingCourseModel.course_id == course_id)
            if teacher_type_id is not None and teacher_type_id != -1:
                q = q.filter(ProfessionalTeachingCourseModel.teacher_type_id == teacher_type_id)
            if deleted_status_id is not None and deleted_status_id != -1:
                q = q.filter(ProfessionalTeachingCourseModel.deleted_status_id == deleted_status_id)
            else:
                # -1 o None: solo devolver activos (deleted_status_id == 0)
                q = q.filter(ProfessionalTeachingCourseModel.deleted_status_id == 0)
            rows = q.all()
            data = [
                {
                    "id": r.id,
                    "professional_id": r.professional_id,
                    "teaching_id": r.teaching_id,
                    "course_id": r.course_id,
                    "teacher_type_id": r.teacher_type_id,
                    "subject": r.subject,
                    "deleted_status_id": r.deleted_status_id,
                    "added_date": r.added_date.isoformat() if r.added_date else None,
                    "updated_date": r.updated_date.isoformat() if r.updated_date else None,
                }
                for r in rows
            ]
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_teacher_type(self, teacher_type_id: int, course_id: int):
        """Lista asignaciones por tipo de profesional (regular/especialista) y course_id con deleted_status_id == 0."""
        try:
            rows = (
                self.db.query(ProfessionalTeachingCourseModel)
                .filter(
                    ProfessionalTeachingCourseModel.teacher_type_id == teacher_type_id,
                    ProfessionalTeachingCourseModel.course_id == course_id,
                    ProfessionalTeachingCourseModel.deleted_status_id == 0,
                )
                .all()
            )
            data = [
                {
                    "id": r.id,
                    "professional_id": r.professional_id,
                    "teaching_id": r.teaching_id,
                    "course_id": r.course_id,
                    "teacher_type_id": r.teacher_type_id,
                    "subject": r.subject,
                    "deleted_status_id": r.deleted_status_id,
                    "added_date": r.added_date.isoformat() if r.added_date else None,
                    "updated_date": r.updated_date.isoformat() if r.updated_date else None,
                }
                for r in rows
            ]
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int):
        """Obtiene una asignaci?n por id (valor en URL)."""
        try:
            row = self.db.query(ProfessionalTeachingCourseModel).filter(
                ProfessionalTeachingCourseModel.id == id
            ).first()
            if not row:
                return {"status": "error", "message": "Asignaci?n no encontrada.", "data": None}
            data = {
                "id": row.id,
                "professional_id": row.professional_id,
                "teaching_id": row.teaching_id,
                "course_id": row.course_id,
                "teacher_type_id": row.teacher_type_id,
                "subject": row.subject,
                "deleted_status_id": row.deleted_status_id,
                "added_date": row.added_date.isoformat() if row.added_date else None,
                "updated_date": row.updated_date.isoformat() if row.updated_date else None,
            }
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def update(self, id: int, data: dict):
        """Edita una asignaci?n por id; solo actualiza los campos enviados."""
        try:
            row = self.db.query(ProfessionalTeachingCourseModel).filter(
                ProfessionalTeachingCourseModel.id == id
            ).first()
            if not row:
                return {"status": "error", "message": "Asignaci?n no encontrada."}
            if data.get("professional_id") is not None:
                row.professional_id = data["professional_id"]
            if data.get("teaching_id") is not None:
                row.teaching_id = data["teaching_id"]
            if data.get("course_id") is not None:
                row.course_id = data["course_id"]
            if "teacher_type_id" in data:
                row.teacher_type_id = data["teacher_type_id"]
            if "subject" in data:
                row.subject = data["subject"]
            if data.get("deleted_status_id") is not None:
                row.deleted_status_id = data["deleted_status_id"]
            row.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Asignaci?n actualizada correctamente.", "data": {"id": row.id}}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def store(self, data: dict):
        """Crea una asignaci?n profesional - ense?anza - curso (una fila)."""
        try:
            new_ptc = ProfessionalTeachingCourseModel(
                professional_id=data.get("professional_id"),
                teaching_id=data.get("teaching_id"),
                course_id=data.get("course_id"),
                teacher_type_id=data.get("teacher_type_id"),
                subject=data.get("subject"),
                deleted_status_id=data.get("deleted_status_id", 0),
                added_date=datetime.now(),
                updated_date=datetime.now(),
            )
            self.db.add(new_ptc)
            self.db.commit()
            self.db.refresh(new_ptc)
            return {
                "status": "success",
                "message": "Asignaci?n creada correctamente",
                "id": new_ptc.id,
            }
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int):
        """Elimina una asignaci?n por ID (borrado l?gico: actualiza deleted_status_id = 1)."""
        try:
            row = self.db.query(ProfessionalTeachingCourseModel).filter(
                ProfessionalTeachingCourseModel.id == id
            ).first()
            if not row:
                return {"status": "error", "message": "Asignaci?n no encontrada."}
            row.deleted_status_id = 1
            row.updated_date = datetime.now()
            self.db.commit()
            return {"status": "success", "message": "Asignaci?n eliminada correctamente."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
