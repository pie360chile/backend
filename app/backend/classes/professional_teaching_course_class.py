from datetime import datetime
from sqlalchemy import func
from app.backend.db.models import (
    ProfessionalTeachingCourseModel,
    ProfessionalModel,
    CareerTypeModel,
    CourseModel,
)


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
            data = []
            for r in rows:
                career_type_id = getattr(r, "career_type_id", None)
                career_type_name = self._get_specialty_for_assignment(r)
                data.append({
                    "id": r.id,
                    "professional_id": r.professional_id,
                    "teaching_id": r.teaching_id,
                    "course_id": r.course_id,
                    "teacher_type_id": r.teacher_type_id,
                    "career_type_id": career_type_id,
                    "career_type_name": career_type_name,
                    "subject": r.subject,
                    "deleted_status_id": r.deleted_status_id,
                    "added_date": r.added_date.isoformat() if r.added_date else None,
                    "updated_date": r.updated_date.isoformat() if r.updated_date else None,
                })
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def _get_specialty_for_professional(self, professional_id):
        if not professional_id:
            return None
        prof = self.db.query(ProfessionalModel).filter(ProfessionalModel.id == professional_id).first()
        if not prof or not prof.career_type_id:
            return None
        ct = self.db.query(CareerTypeModel).filter(CareerTypeModel.id == prof.career_type_id).first()
        return (ct.career_type or "").strip() if ct and ct.career_type else None

    def _get_specialty_for_assignment(self, row):
        """Especialidad: primero career_type_id de la asignación, si no del profesional."""
        assignment_ct_id = getattr(row, "career_type_id", None)
        if assignment_ct_id:
            ct = self.db.query(CareerTypeModel).filter(CareerTypeModel.id == assignment_ct_id).first()
            if ct and ct.career_type:
                return (ct.career_type or "").strip()
        return self._get_specialty_for_professional(row.professional_id)

    def get_professionals_by_course_school_career(
        self,
        course_id: int,
        school_id: int,
        career_type_id: int,
        teacher_type_id: int = -1,
    ):
        """Lista profesionales (nombres, apellidos, rut, teacher_type_id) filtrados por curso, colegio, career_type_id y opcionalmente teacher_type_id (-1 = no filtrar)."""
        try:
            q = (
                self.db.query(
                    ProfessionalModel.id.label("professional_id"),
                    ProfessionalModel.names,
                    ProfessionalModel.lastnames,
                    ProfessionalModel.identification_number,
                    ProfessionalTeachingCourseModel.teacher_type_id,
                )
                .join(
                    ProfessionalTeachingCourseModel,
                    ProfessionalTeachingCourseModel.professional_id == ProfessionalModel.id,
                )
                .join(
                    CourseModel,
                    CourseModel.id == ProfessionalTeachingCourseModel.course_id,
                )
                .filter(
                    ProfessionalTeachingCourseModel.course_id == course_id,
                    CourseModel.school_id == school_id,
                    CourseModel.deleted_status_id == 0,
                    ProfessionalTeachingCourseModel.career_type_id == career_type_id,
                    ProfessionalTeachingCourseModel.deleted_status_id == 0,
                )
            )
            if teacher_type_id is not None and teacher_type_id != -1:
                q = q.filter(ProfessionalTeachingCourseModel.teacher_type_id == teacher_type_id)
            q = q.distinct()
            rows = q.all()
            data = [
                {
                    "professional_id": r.professional_id,
                    "names": (r.names or "").strip() or None,
                    "lastnames": (r.lastnames or "").strip() or None,
                    "rut": (r.identification_number or "").strip() or None,
                    "teacher_type_id": r.teacher_type_id,
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
            data = []
            for r in rows:
                specialty = self._get_specialty_for_assignment(r)
                data.append({
                    "id": r.id,
                    "professional_id": r.professional_id,
                    "teaching_id": r.teaching_id,
                    "course_id": r.course_id,
                    "teacher_type_id": r.teacher_type_id,
                    "career_type_id": getattr(r, "career_type_id", None),
                    "subject": r.subject,
                    "specialty": specialty,
                    "deleted_status_id": r.deleted_status_id,
                    "added_date": r.added_date.isoformat() if r.added_date else None,
                    "updated_date": r.updated_date.isoformat() if r.updated_date else None,
                })
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
            specialty = self._get_specialty_for_assignment(row)
            data = {
                "id": row.id,
                "professional_id": row.professional_id,
                "teaching_id": row.teaching_id,
                "course_id": row.course_id,
                "teacher_type_id": row.teacher_type_id,
                "career_type_id": getattr(row, "career_type_id", None),
                "subject": row.subject,
                "specialty": specialty,
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
            # career_type_id of the assignment (specialty for this assignment)
            if data.get("career_type_id") is not None:
                row.career_type_id = data["career_type_id"]
            elif "specialty" in data:
                specialty_val = data.get("specialty")
                specialty_name = (specialty_val if specialty_val is not None else "").strip() if isinstance(specialty_val, str) else str(specialty_val or "").strip()
                if specialty_name:
                    ct = self.db.query(CareerTypeModel).filter(
                        func.trim(CareerTypeModel.career_type) == specialty_name
                    ).first()
                    if not ct:
                        ct = self.db.query(CareerTypeModel).filter(
                            func.trim(CareerTypeModel.career_type).ilike(specialty_name)
                        ).first()
                    if not ct:
                        ct = self.db.query(CareerTypeModel).filter(
                            CareerTypeModel.career_type.ilike(f"%{specialty_name}%")
                        ).first()
                    if ct:
                        row.career_type_id = ct.id
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
                career_type_id=data.get("career_type_id"),
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
