"""Persist Agents psychoped fields into psychopedagogical_evaluation_info (ficha admin)."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.backend.classes.psychopedagogical_evaluation_class import (
    PsychopedagogicalEvaluationClass,
)
from app.backend.db.models import FolderModel

logger = logging.getLogger(__name__)

PSYCHOPED_DOCUMENT_ID = 27


def _pick_text(replacements: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = replacements.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _parse_date_iso(value: str | None) -> str | None:
    if not value or not str(value).strip():
        return None
    raw = str(value).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            part = raw.split()[0] if fmt.startswith("%d") else raw[:10]
            return datetime.strptime(part, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m2 = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", raw)
    if m2:
        d, mo, y = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        try:
            return datetime(y, mo, d).strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def _admission_from_template(replacements: dict[str, str]) -> tuple[str | None, str | None]:
    """Plantilla admission_type_1|2|3 o form admission_type → (admission_type, other)."""
    raw = _pick_text(replacements, "admission_type").lower()
    other = _pick_text(replacements, "admission_type_other")
    if raw in ("ingreso", "ingreso_pie", "nuevo", "admission"):
        return "ingreso", None
    if raw in ("reevaluacion", "reevaluación", "re_evaluacion", "revaluation"):
        return "reevaluacion", None
    if raw in ("otro", "otra", "otros"):
        return "otro", other or None

    t1 = _pick_text(replacements, "admission_type_1")
    t2 = _pick_text(replacements, "admission_type_2")
    t3 = _pick_text(replacements, "admission_type_3")
    if t1:
        return "ingreso", None
    if t2:
        return "reevaluacion", None
    if t3:
        # Si hay texto distinto de X, guardarlo en other
        other_val = t3 if t3.upper() not in ("X", "SI", "SÍ", "1") else other or None
        return "otro", other_val
    return None, None


def _scales_from_template_marks(replacements: dict[str, str]) -> dict[str, str]:
    """
    scale_{row}_{col}=X en plantilla → pedagogical_scale_N / social_communicative_scale_N.
    Filas 1–10 pedagógicas; 11–20 social (indicador 1–10).
    """
    out: dict[str, str] = {}
    for key, value in replacements.items():
        m = re.fullmatch(r"scale_(\d+)_(\d+)", str(key).strip())
        if not m:
            continue
        mark = str(value or "").strip().upper()
        if mark not in ("X", "1", "SI", "SÍ", "TRUE"):
            continue
        row = int(m.group(1))
        col = int(m.group(2))
        if col < 1 or col > 4:
            continue
        scale_val = "N/O" if col == 4 else str(col)
        if 1 <= row <= 10:
            out[f"pedagogical_scale_{row}"] = scale_val
        elif 11 <= row <= 20:
            out[f"social_communicative_scale_{row - 10}"] = scale_val
    return out


def build_psychoped_store_payload(
    student_id: int,
    replacements: dict[str, str],
    student_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Mapea tags de plantilla / fields del agente → columnas psychopedagogical_evaluation_info."""
    ctx = student_context or {}
    admission_type, admission_other = _admission_from_template(replacements)

    payload: dict[str, Any] = {
        "student_id": student_id,
        "social_name": _pick_text(
            replacements, "social_name", "student_social_name", "nombre_social"
        ),
        "age": _pick_text(replacements, "age", "student_age", "edad"),
        "evaluation_date": _parse_date_iso(
            _pick_text(replacements, "evaluation_date", "fecha_evaluacion")
        ),
        "diagnosis": _pick_text(
            replacements, "diagnosis", "diagnostic", "diagnostico"
        ),
        "diagnosis_issue_date": _parse_date_iso(
            _pick_text(
                replacements,
                "diagnosis_issue_date",
                "issue_date",
                "fecha_emision_diagnostico",
            )
        ),
        "admission_type": admission_type,
        "admission_type_other": admission_other,
        "instruments_applied": _pick_text(
            replacements, "instruments_applied", "instrumentos_aplicados"
        ),
        "school_history_background": _pick_text(
            replacements,
            "school_history_background",
            "antecedentes_historia_escolar",
        ),
        "cognitive_analysis": _pick_text(
            replacements, "cognitive_analysis", "analisis_cognitivo"
        ),
        "personal_analysis": _pick_text(
            replacements, "personal_analysis", "analisis_personal_socioemocional"
        ),
        "motor_analysis": _pick_text(
            replacements, "motor_analysis", "analisis_motor_autonomia_sensorial"
        ),
        "cognitive_synthesis": _pick_text(
            replacements, "cognitive_synthesis", "sintesis_cognitiva"
        ),
        "personal_synthesis": _pick_text(
            replacements, "personal_synthesis", "sintesis_personal"
        ),
        "motor_synthesis": _pick_text(
            replacements, "motor_synthesis", "sintesis_motora"
        ),
        "suggestions_to_school": _pick_text(
            replacements, "suggestions_to_school", "sugerencias_al_establecimiento"
        ),
        "suggestions_to_classroom_team": _pick_text(
            replacements,
            "suggestions_to_classroom_team",
            "sugerencias_al_equipo_de_aula",
        ),
        "suggestions_to_student": _pick_text(
            replacements, "suggestions_to_student", "sugerencias_al_estudiante"
        ),
        "suggestions_to_family": _pick_text(
            replacements, "suggestions_to_family", "sugerencias_a_la_familia"
        ),
        "other_suggestions": _pick_text(
            replacements, "other_suggestions", "otras_sugerencias"
        ),
        "conclusion": _pick_text(
            replacements, "conclusion", "conclusion_informe"
        ),
        "professional_identification_number": _pick_text(
            replacements,
            "professional_identification_number",
            "rut_profesional",
        ),
        "professional_registration_number": _pick_text(
            replacements,
            "professional_registration_number",
            "registro_profesional",
        ),
        "professional_specialty": _pick_text(
            replacements, "professional_specialty", "especialidad_profesional"
        ),
    }

    # Escalas ya en formato form
    for i in range(1, 11):
        ped = _pick_text(replacements, f"pedagogical_scale_{i}")
        if ped:
            payload[f"pedagogical_scale_{i}"] = ped
        soc = _pick_text(replacements, f"social_communicative_scale_{i}")
        if soc:
            payload[f"social_communicative_scale_{i}"] = soc

    # Escalas desde marcas X de la plantilla Word
    for key, val in _scales_from_template_marks(replacements).items():
        payload.setdefault(key, val)

    if ctx.get("professional_id"):
        payload["professional_id"] = ctx.get("professional_id")

    cleaned: dict[str, Any] = {"student_id": student_id}
    for key, value in payload.items():
        if key == "student_id":
            continue
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        cleaned[key] = value
    return cleaned


def persist_psychoped_from_agent(
    db: Session,
    student_id: int,
    replacements: dict[str, str],
    student_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Crea/actualiza psychopedagogical_evaluation_info con el texto del agente."""
    payload = build_psychoped_store_payload(student_id, replacements, student_context)
    result = PsychopedagogicalEvaluationClass(db).store(payload)
    if result.get("status") == "error":
        logger.warning(
            "psychopedagogical_evaluation_info store failed student=%s: %s",
            student_id,
            result.get("message"),
        )
    return result


def link_folder_to_psychoped_evaluation(
    db: Session,
    folder_id: int | None,
    evaluation_id: int | None,
) -> None:
    if not folder_id or not evaluation_id:
        return
    try:
        row = db.query(FolderModel).filter(FolderModel.id == folder_id).first()
        if row is None:
            return
        row.detail_id = int(evaluation_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning(
            "link folder %s to psychoped evaluation %s: %s",
            folder_id,
            evaluation_id,
            exc,
        )
