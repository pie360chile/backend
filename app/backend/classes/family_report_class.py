from typing import Optional, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.backend.db.models import FamilyReportModel


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


class FamilyReportClass:
    def __init__(self, db: Session):
        self.db = db

    def _report_to_dict(self, report: FamilyReportModel) -> dict:
        """Convierte un modelo a dict para respuesta."""
        return {
            "id": report.id,
            "student_id": report.student_id,
            "document_type_id": report.document_type_id,
            "version": report.version,
            "added_date": report.added_date.strftime("%Y-%m-%d %H:%M:%S") if report.added_date else None,
            "updated_date": report.updated_date.strftime("%Y-%m-%d %H:%M:%S") if report.updated_date else None,
            "student_full_name": report.student_full_name,
            "student_identification_number": report.student_identification_number,
            "student_social_name": report.student_social_name,
            "student_born_date": report.student_born_date.strftime("%Y-%m-%d") if report.student_born_date else None,
            "student_age": report.student_age,
            "student_course": report.student_course,
            "student_school": report.student_school,
            "professional_id": report.professional_id,
            "professional_identification_number": report.professional_identification_number,
            "professional_social_name": report.professional_social_name,
            "professional_role": report.professional_role,
            "professional_phone": report.professional_phone,
            "professional_email": report.professional_email,
            "report_delivery_date": report.report_delivery_date.strftime("%Y-%m-%d") if report.report_delivery_date else None,
            "receiver_full_name": report.receiver_full_name,
            "receiver_identification_number": report.receiver_identification_number,
            "receiver_social_name": report.receiver_social_name,
            "receiver_phone": report.receiver_phone,
            "receiver_email": report.receiver_email,
            "receiver_relationship": report.receiver_relationship,
            "receiver_presence_of": report.receiver_presence_of,
            "guardian_type": report.guardian_type,
            "has_power_of_attorney": report.has_power_of_attorney,
            "evaluation_type": report.evaluation_type,
            "evaluation_date": report.evaluation_date.strftime("%Y-%m-%d") if report.evaluation_date else None,
            "applied_instruments": report.applied_instruments,
            "diagnosis": report.diagnosis,
            "pedagogical_strengths": report.pedagogical_strengths,
            "pedagogical_support_needs": report.pedagogical_support_needs,
            "social_affective_strengths": report.social_affective_strengths,
            "social_affective_support_needs": report.social_affective_support_needs,
            "health_strengths": report.health_strengths,
            "health_support_needs": report.health_support_needs,
            "collaborative_work": report.collaborative_work,
            "home_support": report.home_support,
            "agreements_commitments": report.agreements_commitments,
            "evaluation_date_1": report.evaluation_date_1.strftime("%Y-%m-%d") if report.evaluation_date_1 else None,
            "evaluation_date_2": report.evaluation_date_2.strftime("%Y-%m-%d") if report.evaluation_date_2 else None,
            "evaluation_date_3": report.evaluation_date_3.strftime("%Y-%m-%d") if report.evaluation_date_3 else None,
        }

    def get(self, id: int) -> Any:
        """Obtiene un informe familiar por ID."""
        try:
            report = self.db.query(FamilyReportModel).filter(FamilyReportModel.id == id).first()
            if report:
                return self._report_to_dict(report)
            return {"status": "error", "message": "Informe familiar no encontrado."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_by_student_id(self, student_id: int) -> Any:
        """Obtiene el informe familiar más reciente por student_id."""
        try:
            report = (
                self.db.query(FamilyReportModel)
                .filter(FamilyReportModel.student_id == student_id)
                .order_by(FamilyReportModel.id.desc())
                .first()
            )
            if report:
                return self._report_to_dict(report)
            return {"status": "error", "message": "No se encontró informe familiar para este estudiante."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_all(self, student_id: Optional[int] = None) -> Any:
        """Lista informes familiares, opcionalmente filtrados por student_id."""
        try:
            query = self.db.query(FamilyReportModel)
            if student_id is not None:
                query = query.filter(FamilyReportModel.student_id == student_id)
            reports = query.order_by(FamilyReportModel.id.desc()).all()
            return [self._report_to_dict(r) for r in reports]
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def store(self, data: dict) -> Any:
        """
        Almacena un nuevo informe familiar.
        Si ya existe uno para el mismo student_id, incrementa la versión.
        """
        try:
            student_id = data.get("student_id")
            document_type_id = data.get("document_type_id") or 7

            # Obtener última versión para este estudiante
            last_report = (
                self.db.query(FamilyReportModel)
                .filter(
                    FamilyReportModel.student_id == student_id,
                    FamilyReportModel.document_type_id == document_type_id,
                )
                .order_by(FamilyReportModel.version.desc())
                .first()
            )
            version = (last_report.version + 1) if last_report else 1

            new_report = FamilyReportModel(
                student_id=student_id,
                document_type_id=document_type_id,
                version=version,
                student_full_name=data.get("student_full_name"),
                student_identification_number=data.get("student_identification_number"),
                student_social_name=data.get("student_social_name"),
                student_born_date=_parse_date(data.get("student_born_date")),
                student_age=data.get("student_age"),
                student_course=data.get("student_course"),
                student_school=data.get("student_school"),
                professional_id=data.get("professional_id"),
                professional_identification_number=data.get("professional_identification_number"),
                professional_social_name=data.get("professional_social_name"),
                professional_role=data.get("professional_role"),
                professional_phone=data.get("professional_phone"),
                professional_email=data.get("professional_email"),
                report_delivery_date=_parse_date(data.get("report_delivery_date")),
                receiver_full_name=data.get("receiver_full_name"),
                receiver_identification_number=data.get("receiver_identification_number"),
                receiver_social_name=data.get("receiver_social_name"),
                receiver_phone=data.get("receiver_phone"),
                receiver_email=data.get("receiver_email"),
                receiver_relationship=data.get("receiver_relationship"),
                receiver_presence_of=data.get("receiver_presence_of"),
                guardian_type=data.get("guardian_type"),
                has_power_of_attorney=data.get("has_power_of_attorney"),
                evaluation_type=data.get("evaluation_type"),
                evaluation_date=_parse_date(data.get("evaluation_date")),
                applied_instruments=data.get("applied_instruments"),
                diagnosis=data.get("diagnosis"),
                pedagogical_strengths=data.get("pedagogical_strengths"),
                pedagogical_support_needs=data.get("pedagogical_support_needs"),
                social_affective_strengths=data.get("social_affective_strengths"),
                social_affective_support_needs=data.get("social_affective_support_needs"),
                health_strengths=data.get("health_strengths"),
                health_support_needs=data.get("health_support_needs"),
                collaborative_work=data.get("collaborative_work"),
                home_support=data.get("home_support"),
                agreements_commitments=data.get("agreements_commitments"),
                evaluation_date_1=_parse_date(data.get("evaluation_date_1")),
                evaluation_date_2=_parse_date(data.get("evaluation_date_2")),
                evaluation_date_3=_parse_date(data.get("evaluation_date_3")),
                added_date=datetime.now(),
                updated_date=datetime.now(),
            )

            self.db.add(new_report)
            self.db.commit()
            self.db.refresh(new_report)

            return {"status": "success", "message": "Informe familiar creado exitosamente", "id": new_report.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza un informe familiar existente."""
        try:
            report = self.db.query(FamilyReportModel).filter(FamilyReportModel.id == id).first()
            if not report:
                return {"status": "error", "message": "Informe familiar no encontrado."}

            date_fields = {
                "student_born_date",
                "report_delivery_date",
                "evaluation_date",
                "evaluation_date_1",
                "evaluation_date_2",
                "evaluation_date_3",
            }

            for key, value in data.items():
                if hasattr(report, key):
                    if key in date_fields:
                        setattr(report, key, _parse_date(value))
                    else:
                        setattr(report, key, value)

            report.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(report)

            return {"status": "success", "message": "Informe familiar actualizado exitosamente", "id": report.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        """Elimina un informe familiar."""
        try:
            report = self.db.query(FamilyReportModel).filter(FamilyReportModel.id == id).first()
            if not report:
                return {"status": "error", "message": "Informe familiar no encontrado."}
            self.db.delete(report)
            self.db.commit()
            return {"status": "success", "message": "Informe familiar eliminado exitosamente"}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
