"""Router generado desde pedagogical_evaluation_registry — pedagogical_evaluation_classroom_seventh_grade."""
from app.backend.services.pedagogical_evaluation_factory import build_pedagogical_evaluation_router
from app.backend.services.pedagogical_evaluation_registry import PEDAGOGICAL_GRADE_CONFIG_BY_KEY

_cfg = PEDAGOGICAL_GRADE_CONFIG_BY_KEY['pedagogical_evaluation_classroom_seventh_grade']

pedagogical_evaluation_classroom_seventh_grade = build_pedagogical_evaluation_router(
    prefix=_cfg.prefix,
    tag=_cfg.tag,
    model=_cfg.model,
    field_names=_cfg.field_names,
    default_document_type_id=_cfg.default_document_type_id,
    store_schema=_cfg.store_schema,
    update_schema=_cfg.update_schema,
)
