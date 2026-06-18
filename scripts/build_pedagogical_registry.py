"""Genera pedagogical_evaluation_registry.py desde las clases existentes."""
import ast
import glob
import re
from pathlib import Path

CLASSES_DIR = Path(__file__).resolve().parents[1] / "app" / "backend" / "classes"
OUT = Path(__file__).resolve().parents[1] / "app" / "backend" / "services" / "pedagogical_evaluation_registry.py"

ROUTE_META = {
    "pedagogical_evaluation_classroom_first_grade": (31, "Pedagogical Evaluation Classroom First Grade (Document 31)"),
    "pedagogical_evaluation_classroom_second_grade": (32, "Pedagogical Evaluation Classroom Second Grade (Document 32)"),
    "pedagogical_evaluation_classroom_third_grade": (33, "Pedagogical Evaluation Classroom Third Grade (Document 33)"),
    "pedagogical_evaluation_classroom_fourth_grade": (34, "Pedagogical Evaluation Classroom Fourth Grade (Document 34)"),
    "pedagogical_evaluation_classroom_fifth_grade": (35, "Pedagogical Evaluation Classroom Fifth Grade (Document 35)"),
    "pedagogical_evaluation_classroom_sixth_grade": (36, "Pedagogical Evaluation Classroom Sixth Grade (Document 36)"),
    "pedagogical_evaluation_classroom_seventh_grade": (37, "Pedagogical Evaluation Classroom Seventh Grade (Document 37)"),
    "pedagogical_evaluation_classroom_eighth_grade": (38, "Pedagogical Evaluation Classroom Eighth Grade (Document 38)"),
    "pedagogical_evaluation_classroom_first_grade_secondary": (39, "Pedagogical Evaluation Classroom First Grade Secondary (Document 39)"),
    "pedagogical_evaluation_classroom_second_grade_secondary": (40, "Pedagogical Evaluation Classroom Second Grade Secondary (Document 40)"),
}

MODEL_BY_KEY = {
    k: f"{''.join(w.capitalize() for w in k.split('_'))}Model"
    for k in ROUTE_META
}


def extract_field_names(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"_FIELD_NAMES\s*=\s*\[(.*?)\]", text, re.S)
    if not m:
        raise ValueError(f"No _FIELD_NAMES in {path}")
    return re.findall(r'"(\w+)"', m.group(1))


def schema_names(key: str) -> tuple[str, str]:
    base = "".join(w.capitalize() for w in key.split("_"))
    return f"Store{base}", f"Update{base}"


lines = [
    '"""Registro de evaluaciones pedagógicas docente de aula (docs 31–40)."""',
    "",
    "from dataclasses import dataclass",
    "from typing import Sequence, Type",
    "",
    "from app.backend.db import models",
    "from app.backend import schemas",
    "from app.backend.services.pedagogical_evaluation_factory import build_pedagogical_evaluation_router",
    "",
    "",
    "@dataclass(frozen=True)",
    "class PedagogicalGradeConfig:",
    "    key: str",
    "    prefix: str",
    "    tag: str",
    "    model: Type",
    "    field_names: Sequence[str]",
    "    default_document_type_id: int",
    "    store_schema: Type",
    "    update_schema: Type",
    "",
    "",
    "def _cfg(",
    "    key: str,",
    "    field_names: Sequence[str],",
    "    doc_type: int,",
    "    tag: str,",
    ") -> PedagogicalGradeConfig:",
    "    model_name = ''.join(w.capitalize() for w in key.split('_')) + 'Model'",
    "    store_name, update_name = f'Store{model_name.replace(\"Model\", \"\")}', f'Update{model_name.replace(\"Model\", \"\")}'",
    "    return PedagogicalGradeConfig(",
    "        key=key,",
    "        prefix=f'/{key}',",
    "        tag=tag,",
    "        model=getattr(models, model_name),",
    "        field_names=field_names,",
    "        default_document_type_id=doc_type,",
    "        store_schema=getattr(schemas, store_name),",
    "        update_schema=getattr(schemas, update_name),",
    "    )",
    "",
    "",
    "PEDAGOGICAL_GRADE_CONFIGS: list[PedagogicalGradeConfig] = [",
]

for key, (doc_type, tag) in ROUTE_META.items():
    class_path = CLASSES_DIR / f"{key}_class.py"
    fields = extract_field_names(class_path)
    fields_repr = ",\n        ".join(f'"{f}"' for f in fields)
    lines.append(f"    _cfg(")
    lines.append(f'        "{key}",')
    lines.append(f"        [")
    lines.append(f"        {fields_repr},")
    lines.append(f"        ],")
    lines.append(f"        {doc_type},")
    lines.append(f'        "{tag}",')
    lines.append(f"    ),")

lines.extend([
    "]",
    "",
    "PEDAGOGICAL_GRADE_CONFIG_BY_KEY = {c.key: c for c in PEDAGOGICAL_GRADE_CONFIGS}",
    "",
    "",
    "def register_pedagogical_evaluation_routers(app_router) -> None:",
    '    """Monta los 10 routers de evaluación pedagógica desde el registro."""',
    "    for cfg in PEDAGOGICAL_GRADE_CONFIGS:",
    "        router = build_pedagogical_evaluation_router(",
    "            prefix=cfg.prefix,",
    "            tag=cfg.tag,",
    "            model=cfg.model,",
    "            field_names=cfg.field_names,",
    "            default_document_type_id=cfg.default_document_type_id,",
    "            store_schema=cfg.store_schema,",
    "            update_schema=cfg.update_schema,",
    "        )",
    "        app_router.include_router(router)",
    "",
])

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("Wrote", OUT)
