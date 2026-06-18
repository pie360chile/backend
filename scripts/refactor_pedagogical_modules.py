"""Reemplaza routes y classes pedagógicas por wrappers del factory."""
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "app" / "backend"

KEYS = [
    "pedagogical_evaluation_classroom_first_grade",
    "pedagogical_evaluation_classroom_second_grade",
    "pedagogical_evaluation_classroom_third_grade",
    "pedagogical_evaluation_classroom_fourth_grade",
    "pedagogical_evaluation_classroom_fifth_grade",
    "pedagogical_evaluation_classroom_sixth_grade",
    "pedagogical_evaluation_classroom_seventh_grade",
    "pedagogical_evaluation_classroom_eighth_grade",
    "pedagogical_evaluation_classroom_first_grade_secondary",
    "pedagogical_evaluation_classroom_second_grade_secondary",
]

CLASS_NAME = {
    k: "".join(w.capitalize() for w in k.split("_")) + "Class"
    for k in KEYS
}

for key in KEYS:
    route_path = BACKEND / "routes" / f"{key}.py"
    class_path = BACKEND / "classes" / f"{key}_class.py"
    export = key
    cls = CLASS_NAME[key]

    route_path.write_text(
        f'"""Router generado desde pedagogical_evaluation_registry — {key}."""\n'
        f"from app.backend.services.pedagogical_evaluation_factory import build_pedagogical_evaluation_router\n"
        f"from app.backend.services.pedagogical_evaluation_registry import PEDAGOGICAL_GRADE_CONFIG_BY_KEY\n\n"
        f"_cfg = PEDAGOGICAL_GRADE_CONFIG_BY_KEY[{key!r}]\n\n"
        f"{export} = build_pedagogical_evaluation_router(\n"
        f"    prefix=_cfg.prefix,\n"
        f"    tag=_cfg.tag,\n"
        f"    model=_cfg.model,\n"
        f"    field_names=_cfg.field_names,\n"
        f"    default_document_type_id=_cfg.default_document_type_id,\n"
        f"    store_schema=_cfg.store_schema,\n"
        f"    update_schema=_cfg.update_schema,\n"
        f")\n",
        encoding="utf-8",
    )

    class_path.write_text(
        f'"""Servicio generado desde pedagogical_evaluation_registry — {key}."""\n'
        f"from sqlalchemy.orm import Session\n\n"
        f"from app.backend.services.pedagogical_evaluation_factory import PedagogicalEvaluationClassroomService\n"
        f"from app.backend.services.pedagogical_evaluation_registry import PEDAGOGICAL_GRADE_CONFIG_BY_KEY\n\n"
        f"_cfg = PEDAGOGICAL_GRADE_CONFIG_BY_KEY[{key!r}]\n\n\n"
        f"class {cls}(PedagogicalEvaluationClassroomService):\n"
        f"    def __init__(self, db: Session):\n"
        f"        super().__init__(\n"
        f"            db,\n"
        f"            model=_cfg.model,\n"
        f"            field_names=_cfg.field_names,\n"
        f"            default_document_type_id=_cfg.default_document_type_id,\n"
        f"        )\n",
        encoding="utf-8",
    )
    print("Updated", key)
