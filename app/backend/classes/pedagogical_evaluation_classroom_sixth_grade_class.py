"""Servicio generado desde pedagogical_evaluation_registry — pedagogical_evaluation_classroom_sixth_grade."""
from sqlalchemy.orm import Session

from app.backend.services.pedagogical_evaluation_factory import PedagogicalEvaluationClassroomService
from app.backend.services.pedagogical_evaluation_registry import PEDAGOGICAL_GRADE_CONFIG_BY_KEY

_cfg = PEDAGOGICAL_GRADE_CONFIG_BY_KEY['pedagogical_evaluation_classroom_sixth_grade']


class PedagogicalEvaluationClassroomSixthGradeClass(PedagogicalEvaluationClassroomService):
    def __init__(self, db: Session):
        super().__init__(
            db,
            model=_cfg.model,
            field_names=_cfg.field_names,
            default_document_type_id=_cfg.default_document_type_id,
        )
