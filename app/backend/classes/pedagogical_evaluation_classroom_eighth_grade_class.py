"""Document 38 - Pauta de evaluacion pedagogica - Docente de aula - 8vo Basico (eighth grade). Same structure as 7mo."""
from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session
from app.backend.db.models import PedagogicalEvaluationClassroomEighthGradeModel

_FIELD_NAMES = [
    "student_id", "document_type_id", "student_full_name", "student_identification_number",
    "student_born_date", "student_age", "establishment_id", "course", "report_date", "repetitions",
    "professional_id", "report_type", "school_situation_strengths", "observations",
    "attitude_1", "attitude_2", "attitude_3", "attitude_4", "attitude_5", "attitude_6",
    "attitude_7", "attitude_8", "attitude_9", "attitude_10", "attitude_11", "attitude_12", "attitude_13",
    "observations_attitude",
    "language_1", "language_2", "language_3", "language_4", "language_5", "language_6",
    "language_7", "language_8", "language_9", "language_10", "language_11", "language_12", "language_13",
    "language_14", "language_15", "language_16", "language_17",
    "observations_language",
    "reading_type", "comprehension_level", "writing_level",
    "mathematics_1", "mathematics_2", "mathematics_3", "mathematics_4", "mathematics_5",
    "mathematics_6", "mathematics_7", "mathematics_8", "mathematics_9", "mathematics_10",
    "mathematics_11", "mathematics_12", "mathematics_13", "mathematics_14", "mathematics_15",
    "mathematics_16", "mathematics_17",
    "observations_mathematics",
]
_DATE_FIELDS = {"student_born_date", "report_date"}


def _parse_date(val):
    if val is None or val == "":
        return None
    if hasattr(val, "isoformat"):
        return val
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _row_to_dict(r: PedagogicalEvaluationClassroomEighthGradeModel) -> dict:
    out = {"id": r.id, "student_id": r.student_id, "document_type_id": r.document_type_id}
    for name in _FIELD_NAMES:
        if name in ("student_id", "document_type_id"):
            continue
        val = getattr(r, name, None)
        if val is not None and name in _DATE_FIELDS and hasattr(val, "isoformat"):
            val = val.isoformat()
        out[name] = val
    return out


def _payload_to_row_values(payload: dict) -> dict:
    data = {}
    for name in _FIELD_NAMES:
        if name not in payload:
            continue
        val = payload.get(name)
        if name in _DATE_FIELDS:
            val = _parse_date(val)
        data[name] = val
    return data


class PedagogicalEvaluationClassroomEighthGradeClass:
    def __init__(self, db: Session):
        self.db = db

    def _to_dict(self, r: PedagogicalEvaluationClassroomEighthGradeModel) -> dict:
        return _row_to_dict(r)

    def get(self, id: int) -> Any:
        try:
            r = self.db.query(PedagogicalEvaluationClassroomEighthGradeModel).filter(PedagogicalEvaluationClassroomEighthGradeModel.id == id).first()
            if r:
                return self._to_dict(r)
            return {"status": "error", "message": "Informe no encontrado."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_by_student_id(self, student_id: int) -> Any:
        try:
            r = (
                self.db.query(PedagogicalEvaluationClassroomEighthGradeModel)
                .filter(PedagogicalEvaluationClassroomEighthGradeModel.student_id == student_id)
                .order_by(PedagogicalEvaluationClassroomEighthGradeModel.id.desc())
                .first()
            )
            if r:
                return self._to_dict(r)
            return {"status": "error", "message": "No hay informe para este estudiante."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def store(self, payload: dict) -> Any:
        try:
            data = _payload_to_row_values(payload)
            student_id = data.get("student_id") or payload.get("student_id")
            document_type_id = data.get("document_type_id") if data.get("document_type_id") is not None else payload.get("document_type_id", 37)
            if not student_id:
                return {"status": "error", "message": "Falta student_id."}
            data["student_id"] = student_id
            data["document_type_id"] = document_type_id
            row = PedagogicalEvaluationClassroomEighthGradeModel(**{k: v for k, v in data.items() if k in _FIELD_NAMES})
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Informe guardado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, payload: dict) -> Any:
        try:
            row = self.db.query(PedagogicalEvaluationClassroomEighthGradeModel).filter(PedagogicalEvaluationClassroomEighthGradeModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Informe no encontrado."}
            data = _payload_to_row_values(payload)
            for name, value in data.items():
                if name in ("student_id", "document_type_id") and value is None:
                    continue
                if hasattr(row, name):
                    setattr(row, name, value)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Informe actualizado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
