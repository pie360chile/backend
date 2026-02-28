"""Document 27: Psychopedagogical Evaluation Information – info + scale (VII/VIII)."""

from datetime import datetime, date
from typing import Optional, Any, List
from sqlalchemy.orm import Session
from app.backend.db.models import (
    PsychopedagogicalEvaluationInfoModel,
    PsychopedagogicalEvaluationScaleModel,
)


def _serialize_date(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v) if v else None


def _parse_date(s: Optional[str]) -> Optional[date]:
    if s is None or (isinstance(s, str) and not s.strip()):
        return None
    if isinstance(s, date):
        return s
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


VALID_SCALE_TYPES = ("pedagogical", "social_communicative")
VALID_VALUES = ("1", "2", "3", "N/O")


def _info_to_dict(row: PsychopedagogicalEvaluationInfoModel) -> dict:
    return {
        "id": row.id,
        "student_id": row.student_id,
        "social_name": row.social_name,
        "age": row.age,
        "evaluation_date": _serialize_date(row.evaluation_date),
        "diagnosis": row.diagnosis,
        "diagnosis_issue_date": _serialize_date(row.diagnosis_issue_date),
        "admission_type": row.admission_type,
        "admission_type_other": row.admission_type_other,
        "instruments_applied": row.instruments_applied,
        "school_history_background": row.school_history_background,
        "cognitive_analysis": row.cognitive_analysis,
        "personal_analysis": row.personal_analysis,
        "cognitive_synthesis": row.cognitive_synthesis,
        "personal_synthesis": row.personal_synthesis,
        "motor_synthesis": row.motor_synthesis,
        "suggestions_to_school": row.suggestions_to_school,
        "suggestions_to_classroom_team": row.suggestions_to_classroom_team,
        "suggestions_to_student": row.suggestions_to_student,
        "suggestions_to_family": row.suggestions_to_family,
        "other_suggestions": row.other_suggestions,
        "conclusion": row.conclusion,
        "professional_id": row.professional_id,
        "professional_identification_number": row.professional_identification_number,
        "professional_registration_number": row.professional_registration_number,
        "professional_specialty": row.professional_specialty,
        "created_at": _serialize_date(row.created_at),
        "updated_at": _serialize_date(row.updated_at),
    }


def _scale_to_dict(row: PsychopedagogicalEvaluationScaleModel) -> dict:
    return {
        "id": row.id,
        "psychopedagogical_evaluation_info_id": row.psychopedagogical_evaluation_info_id,
        "scale_type": row.scale_type,
        "indicator_number": row.indicator_number,
        "value": row.value,
        "created_at": _serialize_date(row.created_at),
    }


class PsychopedagogicalEvaluationClass:
    def __init__(self, db: Session):
        self.db = db

    def _get_scales(self, eval_info_id: int) -> List[dict]:
        rows = (
            self.db.query(PsychopedagogicalEvaluationScaleModel)
            .filter(PsychopedagogicalEvaluationScaleModel.psychopedagogical_evaluation_info_id == eval_info_id)
            .order_by(
                PsychopedagogicalEvaluationScaleModel.scale_type,
                PsychopedagogicalEvaluationScaleModel.indicator_number,
            )
            .all()
        )
        return [_scale_to_dict(r) for r in rows]

    def get_by_id(self, id: int) -> Any:
        """Obtiene evaluación por id (incluye scales)."""
        try:
            row = self.db.query(PsychopedagogicalEvaluationInfoModel).filter(PsychopedagogicalEvaluationInfoModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            data = _info_to_dict(row)
            data["scales"] = self._get_scales(row.id)
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def get_by_student_id(self, student_id: int, latest_only: bool = True) -> Any:
        """Lista evaluaciones del estudiante; si latest_only=True devuelve solo la más reciente (con scales)."""
        try:
            q = self.db.query(PsychopedagogicalEvaluationInfoModel).filter(
                PsychopedagogicalEvaluationInfoModel.student_id == student_id
            ).order_by(PsychopedagogicalEvaluationInfoModel.id.desc())
            if latest_only:
                row = q.first()
                if not row:
                    return {"status": "success", "data": None}
                data = _info_to_dict(row)
                data["scales"] = self._get_scales(row.id)
                return {"status": "success", "data": data}
            rows = q.all()
            result = []
            for row in rows:
                d = _info_to_dict(row)
                d["scales"] = self._get_scales(row.id)
                result.append(d)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def _validate_scale(self, scale_type: str, indicator_number: int, value: str) -> Optional[str]:
        if scale_type not in VALID_SCALE_TYPES:
            return f"scale_type debe ser {VALID_SCALE_TYPES}"
        if not (1 <= indicator_number <= 10):
            return "indicator_number debe estar entre 1 y 10"
        if value not in VALID_VALUES:
            return f"value debe ser uno de {VALID_VALUES}"
        return None

    def _save_scales(self, eval_info_id: int, scales: List[dict]) -> None:
        self.db.query(PsychopedagogicalEvaluationScaleModel).filter(
            PsychopedagogicalEvaluationScaleModel.psychopedagogical_evaluation_info_id == eval_info_id,
        ).delete(synchronize_session=False)
        now = datetime.utcnow()
        for s in scales or []:
            scale_type = (s.get("scale_type") or "").strip()
            indicator_number = int(s.get("indicator_number", 0))
            value = (s.get("value") or "").strip()
            err = self._validate_scale(scale_type, indicator_number, value)
            if err:
                raise ValueError(err)
            self.db.add(PsychopedagogicalEvaluationScaleModel(
                psychopedagogical_evaluation_info_id=eval_info_id,
                scale_type=scale_type,
                indicator_number=indicator_number,
                value=value,
                created_at=now,
            ))

    def store(self, data: dict) -> Any:
        """Crea o actualiza evaluación por estudiante: si ya existe una para el student_id, se actualiza; si no, se crea."""
        try:
            student_id = int(data.get("student_id"))
            if not student_id:
                return {"status": "error", "message": "student_id es requerido.", "data": None}

            existing = (
                self.db.query(PsychopedagogicalEvaluationInfoModel)
                .filter(PsychopedagogicalEvaluationInfoModel.student_id == student_id)
                .order_by(PsychopedagogicalEvaluationInfoModel.id.desc())
                .first()
            )
            if existing:
                return self.update(existing.id, data)

            row = PsychopedagogicalEvaluationInfoModel(
                student_id=student_id,
                social_name=(data.get("social_name") or "").strip() or None,
                age=(data.get("age") or "").strip() or None,
                evaluation_date=_parse_date(data.get("evaluation_date")),
                diagnosis=(data.get("diagnosis") or "").strip() or None,
                diagnosis_issue_date=_parse_date(data.get("diagnosis_issue_date")),
                admission_type=(data.get("admission_type") or "").strip() or None,
                admission_type_other=(data.get("admission_type_other") or "").strip() or None,
                instruments_applied=(data.get("instruments_applied") or "").strip() or None,
                school_history_background=(data.get("school_history_background") or "").strip() or None,
                cognitive_analysis=(data.get("cognitive_analysis") or "").strip() or None,
                personal_analysis=(data.get("personal_analysis") or "").strip() or None,
                cognitive_synthesis=(data.get("cognitive_synthesis") or "").strip() or None,
                personal_synthesis=(data.get("personal_synthesis") or "").strip() or None,
                motor_synthesis=(data.get("motor_synthesis") or "").strip() or None,
                suggestions_to_school=(data.get("suggestions_to_school") or "").strip() or None,
                suggestions_to_classroom_team=(data.get("suggestions_to_classroom_team") or "").strip() or None,
                suggestions_to_student=(data.get("suggestions_to_student") or "").strip() or None,
                suggestions_to_family=(data.get("suggestions_to_family") or "").strip() or None,
                other_suggestions=(data.get("other_suggestions") or "").strip() or None,
                conclusion=(data.get("conclusion") or "").strip() or None,
                professional_id=int(data["professional_id"]) if data.get("professional_id") is not None else None,
                professional_identification_number=(data.get("professional_identification_number") or "").strip() or None,
                professional_registration_number=(data.get("professional_registration_number") or "").strip() or None,
                professional_specialty=(data.get("professional_specialty") or "").strip() or None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(row)
            self.db.flush()
            scales = data.get("scales") or []
            if isinstance(scales, list):
                self._save_scales(row.id, scales)
            self.db.commit()
            self.db.refresh(row)
            out = _info_to_dict(row)
            out["scales"] = self._get_scales(row.id)
            return {"status": "success", "message": "Evaluación creada.", "id": row.id, "data": out, "created": True}
        except ValueError as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza evaluación por id (y reemplaza scales si vienen en data)."""
        try:
            row = self.db.query(PsychopedagogicalEvaluationInfoModel).filter(PsychopedagogicalEvaluationInfoModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}

            def set_str(key, attr):
                if key in data and data[key] is not None:
                    setattr(row, attr, (data[key] or "").strip() or None)
            def set_date(key, attr):
                if key in data and data[key] is not None:
                    setattr(row, attr, _parse_date(data[key]))
            def set_int(key, attr):
                if key in data:
                    setattr(row, attr, int(data[key]) if data[key] is not None else None)

            set_str("social_name", "social_name")
            set_str("age", "age")
            set_date("evaluation_date", "evaluation_date")
            set_str("diagnosis", "diagnosis")
            set_date("diagnosis_issue_date", "diagnosis_issue_date")
            set_str("admission_type", "admission_type")
            set_str("admission_type_other", "admission_type_other")
            set_str("instruments_applied", "instruments_applied")
            set_str("school_history_background", "school_history_background")
            set_str("cognitive_analysis", "cognitive_analysis")
            set_str("personal_analysis", "personal_analysis")
            set_str("cognitive_synthesis", "cognitive_synthesis")
            set_str("personal_synthesis", "personal_synthesis")
            set_str("motor_synthesis", "motor_synthesis")
            set_str("suggestions_to_school", "suggestions_to_school")
            set_str("suggestions_to_classroom_team", "suggestions_to_classroom_team")
            set_str("suggestions_to_student", "suggestions_to_student")
            set_str("suggestions_to_family", "suggestions_to_family")
            set_str("other_suggestions", "other_suggestions")
            set_str("conclusion", "conclusion")
            set_int("professional_id", "professional_id")
            set_str("professional_identification_number", "professional_identification_number")
            set_str("professional_registration_number", "professional_registration_number")
            set_str("professional_specialty", "professional_specialty")
            row.updated_at = datetime.utcnow()

            if "scales" in data and isinstance(data["scales"], list):
                self._save_scales(row.id, data["scales"])
            self.db.commit()
            self.db.refresh(row)
            out = _info_to_dict(row)
            out["scales"] = self._get_scales(row.id)
            return {"status": "success", "message": "Evaluación actualizada.", "id": id, "data": out, "created": False}
        except ValueError as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}

    def delete(self, id: int) -> Any:
        """Elimina evaluación por id (cascade borra scales)."""
        try:
            row = self.db.query(PsychopedagogicalEvaluationInfoModel).filter(PsychopedagogicalEvaluationInfoModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            self.db.delete(row)
            self.db.commit()
            return {"status": "success", "message": "Evaluación eliminada."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
