from typing import Optional, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.backend.db.models import InterconsultationModel


def _parse_date(value) -> Optional[date]:
    """Convierte string a date si es necesario."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


class InterconsultationClass:
    def __init__(self, db: Session):
        self.db = db

    def _to_dict(self, obj: InterconsultationModel) -> dict:
        """Convierte un modelo a dict para respuesta."""
        return {
            "id": obj.id,
            "student_id": obj.student_id,
            "document_type_id": obj.document_type_id,
            "full_name": obj.full_name,
            "gender_id": obj.gender_id,
            "identification_number": obj.identification_number,
            "born_date": obj.born_date.strftime("%Y-%m-%d") if obj.born_date else None,
            "age": obj.age,
            "nationality_id": obj.nationality_id,
            "native_language": obj.native_language,
            "language_usually_used": obj.language_usually_used,
            "address": obj.address,
            "region_id": obj.region_id,
            "commune_id": obj.commune_id,
            "city": obj.city,
            "responsible_id": obj.responsible_id,
            "contact_phone": obj.contact_phone,
            "contact_email": obj.contact_email,
            "educational_establishment": obj.educational_establishment,
            "course_level": obj.course_level,
            "program_type_id": obj.program_type_id,
            "establishment_address": obj.establishment_address,
            "establishment_commune": obj.establishment_commune,
            "establishment_phone": obj.establishment_phone,
            "establishment_email": obj.establishment_email,
            "additional_information_id": obj.additional_information_id,
            "question_to_answer": obj.question_to_answer,
            "attached_documents": obj.attached_documents,
            "referring_professional": obj.referring_professional,
            "reception_date": obj.reception_date.strftime("%Y-%m-%d") if obj.reception_date else None,
            "evaluation_summary": obj.evaluation_summary,
            "indications_support": obj.indications_support,
            "professional_id": obj.professional_id,
            "professional_identification_number": obj.professional_identification_number,
            "professional_registration_number": obj.professional_registration_number,
            "professional_specialty": obj.professional_specialty,
            "procedence_id": obj.procedence_id,
            "procedence_other": obj.procedence_other,
            "professional_contact_phone": obj.professional_contact_phone,
            "evaluation_date": obj.evaluation_date.strftime("%Y-%m-%d") if obj.evaluation_date else None,
            "required_new_control_id": obj.required_new_control_id,
            "new_control_date": obj.new_control_date.strftime("%Y-%m-%d") if obj.new_control_date else None,
            "added_date": obj.added_date.strftime("%Y-%m-%d %H:%M:%S") if obj.added_date else None,
            "updated_date": obj.updated_date.strftime("%Y-%m-%d %H:%M:%S") if obj.updated_date else None,
        }

    def get(self, id: int) -> Any:
        """Obtiene una interconsulta por ID."""
        try:
            obj = self.db.query(InterconsultationModel).filter(InterconsultationModel.id == id).first()
            if obj:
                return self._to_dict(obj)
            return {"status": "error", "message": "Interconsulta no encontrada."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_by_student_id(self, student_id: int) -> Any:
        """Obtiene la interconsulta más reciente por student_id."""
        try:
            obj = (
                self.db.query(InterconsultationModel)
                .filter(InterconsultationModel.student_id == student_id)
                .order_by(InterconsultationModel.id.desc())
                .first()
            )
            if obj:
                return self._to_dict(obj)
            return {"status": "error", "message": "No se encontró interconsulta para este estudiante."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_all(self, student_id: Optional[int] = None) -> Any:
        """Lista interconsultas, opcionalmente filtradas por student_id."""
        try:
            query = self.db.query(InterconsultationModel)
            if student_id is not None:
                query = query.filter(InterconsultationModel.student_id == student_id)
            items = query.order_by(InterconsultationModel.id.desc()).all()
            return [self._to_dict(i) for i in items]
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def store(self, data: dict) -> Any:
        """
        Crea o actualiza interconsulta.
        Si ya existe una para el mismo student_id, actualiza; si no, crea nueva.
        """
        try:
            student_id = data.get("student_id")
            if student_id is None:
                return {"status": "error", "message": "student_id es requerido."}

            existing = (
                self.db.query(InterconsultationModel)
                .filter(
                    InterconsultationModel.student_id == student_id,
                    InterconsultationModel.document_type_id == data.get("document_type_id", 24),
                )
                .order_by(InterconsultationModel.id.desc())
                .first()
            )
            if existing:
                return self.update(existing.id, data)

            new_obj = InterconsultationModel(
                student_id=data.get("student_id"),
                document_type_id=data.get("document_type_id", 24),
                full_name=data.get("full_name"),
                gender_id=data.get("gender_id"),
                identification_number=data.get("identification_number"),
                born_date=_parse_date(data.get("born_date")),
                age=data.get("age"),
                nationality_id=data.get("nationality_id"),
                native_language=data.get("native_language"),
                language_usually_used=data.get("language_usually_used"),
                address=data.get("address"),
                region_id=data.get("region_id"),
                commune_id=data.get("commune_id"),
                city=data.get("city"),
                responsible_id=data.get("responsible_id"),
                contact_phone=data.get("contact_phone"),
                contact_email=data.get("contact_email"),
                educational_establishment=data.get("educational_establishment"),
                course_level=data.get("course_level"),
                program_type_id=data.get("program_type_id"),
                establishment_address=data.get("establishment_address"),
                establishment_commune=data.get("establishment_commune"),
                establishment_phone=data.get("establishment_phone"),
                establishment_email=data.get("establishment_email"),
                additional_information_id=data.get("additional_information_id"),
                question_to_answer=data.get("question_to_answer"),
                attached_documents=data.get("attached_documents"),
                referring_professional=data.get("referring_professional"),
                reception_date=_parse_date(data.get("reception_date")),
                evaluation_summary=data.get("evaluation_summary"),
                indications_support=data.get("indications_support"),
                professional_id=data.get("professional_id"),
                professional_identification_number=data.get("professional_identification_number"),
                professional_registration_number=data.get("professional_registration_number"),
                professional_specialty=data.get("professional_specialty"),
                procedence_id=data.get("procedence_id"),
                procedence_other=data.get("procedence_other"),
                professional_contact_phone=data.get("professional_contact_phone"),
                evaluation_date=_parse_date(data.get("evaluation_date")),
                required_new_control_id=data.get("required_new_control_id"),
                new_control_date=_parse_date(data.get("new_control_date")),
            )

            self.db.add(new_obj)
            self.db.commit()
            self.db.refresh(new_obj)

            return {"status": "success", "message": "Interconsulta creada exitosamente", "id": new_obj.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza una interconsulta existente."""
        try:
            obj = self.db.query(InterconsultationModel).filter(InterconsultationModel.id == id).first()
            if not obj:
                return {"status": "error", "message": "Interconsulta no encontrada."}

            date_fields = {"born_date", "reception_date", "evaluation_date", "new_control_date"}

            for key, value in data.items():
                if hasattr(obj, key):
                    if key in date_fields:
                        setattr(obj, key, _parse_date(value))
                    else:
                        setattr(obj, key, value)

            obj.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(obj)

            return {"status": "success", "message": "Interconsulta actualizada exitosamente", "id": obj.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        """Elimina una interconsulta."""
        try:
            obj = self.db.query(InterconsultationModel).filter(InterconsultationModel.id == id).first()
            if not obj:
                return {"status": "error", "message": "Interconsulta no encontrada."}
            self.db.delete(obj)
            self.db.commit()
            return {"status": "success", "message": "Interconsulta eliminada exitosamente"}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
