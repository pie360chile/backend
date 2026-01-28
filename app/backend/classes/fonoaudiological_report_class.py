from typing import Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime, date
import json
from app.backend.db.models import FonoaudiologicalReportModel


def _parse_responsible_professionals(val):
    if val is None:
        return None
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return None
    return None


def _serialize_responsible_professionals(val) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, list):
        return json.dumps(val)
    if isinstance(val, str):
        return val
    return None


class FonoaudiologicalReportClass:
    def __init__(self, db: Session):
        self.db = db

    def _to_dict(self, r: FonoaudiologicalReportModel) -> dict:
        return {
            "id": r.id,
            "student_id": r.student_id,
            "document_type_id": r.document_type_id,
            "student_full_name": r.student_full_name,
            "student_identification_number": r.student_identification_number,
            "student_born_date": r.student_born_date.strftime("%Y-%m-%d") if r.student_born_date else None,
            "establishment_id": r.establishment_id,
            "course_id": r.course_id,
            "responsible_professionals": _parse_responsible_professionals(r.responsible_professionals),
            "report_date": r.report_date.strftime("%Y-%m-%d") if r.report_date else None,
            "type_id": r.type_id,
            "reason_evaluation": r.reason_evaluation,
            "evaluation_instruments": r.evaluation_instruments,
            "relevant_background": r.relevant_background,
            "behaviors_observed": r.behaviors_observed,
            "orofacial_auditory": r.orofacial_auditory,
            "phonological_level": r.phonological_level,
            "morphosyntactic_level": r.morphosyntactic_level,
            "semantic_level": r.semantic_level,
            "pragmatic_level": r.pragmatic_level,
            "additional_observations": r.additional_observations,
            "diagnostic_synthesis": r.diagnostic_synthesis,
            "suggestions_family": r.suggestions_family,
            "suggestions_establishment": r.suggestions_establishment,
            "added_date": r.added_date.strftime("%Y-%m-%d %H:%M:%S") if r.added_date else None,
            "updated_date": r.updated_date.strftime("%Y-%m-%d %H:%M:%S") if r.updated_date else None,
        }

    def get(self, id: int) -> Any:
        try:
            r = self.db.query(FonoaudiologicalReportModel).filter(
                FonoaudiologicalReportModel.id == id,
                FonoaudiologicalReportModel.deleted_date == None
            ).first()
            if r:
                return self._to_dict(r)
            return {"status": "error", "message": "Informe fonoaudiológico no encontrado."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_by_student_id(self, student_id: int) -> Any:
        try:
            r = self.db.query(FonoaudiologicalReportModel).filter(
                FonoaudiologicalReportModel.student_id == student_id,
                FonoaudiologicalReportModel.deleted_date == None
            ).order_by(FonoaudiologicalReportModel.id.desc()).first()
            if r:
                return self._to_dict(r)
            return {"status": "error", "message": "No hay informe fonoaudiológico para el estudiante especificado."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_all(self, student_id: Optional[int] = None) -> Any:
        try:
            query = self.db.query(FonoaudiologicalReportModel).filter(
                FonoaudiologicalReportModel.deleted_date == None
            )
            if student_id is not None:
                query = query.filter(FonoaudiologicalReportModel.student_id == student_id)
            rows = query.order_by(FonoaudiologicalReportModel.id.desc()).all()
            return [self._to_dict(r) for r in rows]
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _parse_date(self, v):
        if not v:
            return None
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except Exception:
                return None
        return None

    def store(self, data: dict) -> Any:
        try:
            student_born = self._parse_date(data.get("student_born_date"))
            report_date = self._parse_date(data.get("report_date"))
            rp = _serialize_responsible_professionals(data.get("responsible_professionals"))

            new_r = FonoaudiologicalReportModel(
                student_id=data.get("student_id"),
                document_type_id=data.get("document_type_id", 8),
                student_full_name=data.get("student_full_name"),
                student_identification_number=data.get("student_identification_number"),
                student_born_date=student_born,
                establishment_id=data.get("establishment_id"),
                course_id=data.get("course_id"),
                responsible_professionals=rp,
                report_date=report_date,
                type_id=data.get("type_id"),
                reason_evaluation=data.get("reason_evaluation"),
                evaluation_instruments=data.get("evaluation_instruments"),
                relevant_background=data.get("relevant_background"),
                behaviors_observed=data.get("behaviors_observed"),
                orofacial_auditory=data.get("orofacial_auditory"),
                phonological_level=data.get("phonological_level"),
                morphosyntactic_level=data.get("morphosyntactic_level"),
                semantic_level=data.get("semantic_level"),
                pragmatic_level=data.get("pragmatic_level"),
                additional_observations=data.get("additional_observations"),
                diagnostic_synthesis=data.get("diagnostic_synthesis"),
                suggestions_family=data.get("suggestions_family"),
                suggestions_establishment=data.get("suggestions_establishment"),
                added_date=datetime.now(),
                updated_date=datetime.now(),
            )
            self.db.add(new_r)
            self.db.commit()
            self.db.refresh(new_r)
            return {"status": "success", "message": "Informe fonoaudiológico creado exitosamente.", "id": new_r.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        try:
            r = self.db.query(FonoaudiologicalReportModel).filter(
                FonoaudiologicalReportModel.id == id,
                FonoaudiologicalReportModel.deleted_date == None
            ).first()
            if not r:
                return {"status": "error", "message": "Informe fonoaudiológico no encontrado."}

            if "student_id" in data:
                r.student_id = data["student_id"]
            if "document_type_id" in data:
                r.document_type_id = data["document_type_id"]
            if "student_full_name" in data:
                r.student_full_name = data["student_full_name"]
            if "student_identification_number" in data:
                r.student_identification_number = data["student_identification_number"]
            if "student_born_date" in data:
                r.student_born_date = self._parse_date(data["student_born_date"])
            if "establishment_id" in data:
                r.establishment_id = data["establishment_id"]
            if "course_id" in data:
                r.course_id = data["course_id"]
            if "responsible_professionals" in data:
                r.responsible_professionals = _serialize_responsible_professionals(data["responsible_professionals"])
            if "report_date" in data:
                r.report_date = self._parse_date(data["report_date"])
            if "type_id" in data:
                r.type_id = data["type_id"]
            if "reason_evaluation" in data:
                r.reason_evaluation = data["reason_evaluation"]
            if "evaluation_instruments" in data:
                r.evaluation_instruments = data["evaluation_instruments"]
            if "relevant_background" in data:
                r.relevant_background = data["relevant_background"]
            if "behaviors_observed" in data:
                r.behaviors_observed = data["behaviors_observed"]
            if "orofacial_auditory" in data:
                r.orofacial_auditory = data["orofacial_auditory"]
            if "phonological_level" in data:
                r.phonological_level = data["phonological_level"]
            if "morphosyntactic_level" in data:
                r.morphosyntactic_level = data["morphosyntactic_level"]
            if "semantic_level" in data:
                r.semantic_level = data["semantic_level"]
            if "pragmatic_level" in data:
                r.pragmatic_level = data["pragmatic_level"]
            if "additional_observations" in data:
                r.additional_observations = data["additional_observations"]
            if "diagnostic_synthesis" in data:
                r.diagnostic_synthesis = data["diagnostic_synthesis"]
            if "suggestions_family" in data:
                r.suggestions_family = data["suggestions_family"]
            if "suggestions_establishment" in data:
                r.suggestions_establishment = data["suggestions_establishment"]

            r.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(r)
            return {"status": "success", "message": "Informe fonoaudiológico actualizado exitosamente.", "id": r.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        try:
            r = self.db.query(FonoaudiologicalReportModel).filter(
                FonoaudiologicalReportModel.id == id,
                FonoaudiologicalReportModel.deleted_date == None
            ).first()
            if not r:
                return {"status": "error", "message": "Informe fonoaudiológico no encontrado."}
            r.deleted_date = datetime.now()
            r.updated_date = datetime.now()
            self.db.commit()
            return {"status": "success", "message": "Informe fonoaudiológico eliminado exitosamente."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
