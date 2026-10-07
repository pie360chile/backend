"""Informe psicopedagógico guardado en psychopedagogical_evaluation_info."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.backend.db.models.pie_core import PsychopedagogicalEvaluationInfoModel

# Sin alguno de estos textos no hay informe utilizable para la familia.
_NARRATIVE_ATTRS: tuple[str, ...] = (
    "school_history_background",
    "cognitive_analysis",
    "personal_analysis",
    "motor_analysis",
    "cognitive_synthesis",
    "personal_synthesis",
    "motor_synthesis",
    "conclusion",
    "suggestions_to_school",
    "suggestions_to_classroom_team",
    "suggestions_to_student",
    "suggestions_to_family",
    "other_suggestions",
)

_FIELDS: tuple[tuple[str, str], ...] = (
    ("diagnosis", "Diagnóstico"),
    ("diagnosis_issue_date", "Fecha de emisión del diagnóstico"),
    ("evaluation_date", "Fecha de evaluación"),
    ("admission_type", "Tipo de ingreso"),
    ("admission_type_other", "Otro tipo de ingreso"),
    ("instruments_applied", "Instrumentos aplicados"),
    ("school_history_background", "Antecedentes de historia escolar"),
    ("cognitive_analysis", "Análisis cognitivo"),
    ("personal_analysis", "Análisis personal / socioemocional"),
    ("motor_analysis", "Análisis motor"),
    ("cognitive_synthesis", "Síntesis cognitiva"),
    ("personal_synthesis", "Síntesis personal"),
    ("motor_synthesis", "Síntesis motora"),
    ("conclusion", "Conclusión"),
    ("suggestions_to_school", "Sugerencias al establecimiento"),
    ("suggestions_to_classroom_team", "Sugerencias al equipo de aula"),
    ("suggestions_to_student", "Sugerencias al estudiante"),
    ("suggestions_to_family", "Sugerencias a la familia"),
    ("other_suggestions", "Otras sugerencias"),
    ("professional_specialty", "Especialidad del profesional"),
)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def student_has_usable_psychoped_report(db: Session, student_id: int) -> bool:
    """True solo si la ficha guardada trae análisis, síntesis, conclusión o sugerencias."""
    if int(student_id) < 1:
        return False
    row = (
        db.query(PsychopedagogicalEvaluationInfoModel)
        .filter(PsychopedagogicalEvaluationInfoModel.student_id == int(student_id))
        .order_by(PsychopedagogicalEvaluationInfoModel.id.desc())
        .first()
    )
    if row is None:
        return False
    for key in _NARRATIVE_ATTRS:
        if len(_text(getattr(row, key, None))) >= 40:
            return True
    return False


def build_saved_psychoped_context(
    db: Session,
    *,
    student_id: int,
    student_name: str | None = None,
    student_rut: str | None = None,
) -> dict[str, Any] | None:
    """
    Última ficha psychopedagogical_evaluation_info del estudiante.

    None si no hay fila.
    """
    if not student_id or int(student_id) < 1:
        return None

    row = (
        db.query(PsychopedagogicalEvaluationInfoModel)
        .filter(PsychopedagogicalEvaluationInfoModel.student_id == int(student_id))
        .order_by(PsychopedagogicalEvaluationInfoModel.id.desc())
        .first()
    )
    if row is None:
        return None

    lines: list[str] = []
    for key, label in _FIELDS:
        text = _text(getattr(row, key, None))
        if text:
            lines.append(f"- {label}: {text}")

    who = (student_name or "").strip() or (student_rut or "").strip() or f"student_id={int(student_id)}"
    updated = getattr(row, "updated_at", None) or getattr(row, "created_at", None)
    when = updated.isoformat(sep=" ", timespec="seconds") if hasattr(updated, "isoformat") else ""

    parts = [
        "INFORME PSICOPEDAGÓGICO GUARDADO EN PIE360 "
        "(tabla psychopedagogical_evaluation_info). "
        "Fuente MCP: get_saved_psychopedagogical_evaluation. "
        "Es la ficha que quedó grabada al generar el informe psicopedagógico. "
        "OBLIGATORIO para el Informe a la Familia: redacta motivos, instrumentos, "
        "diagnóstico, fortalezas, necesidades, apoyos y acuerdos desde ESTE texto. "
        "No lo ignores. No digas que no hay antecedentes de evaluación si este bloque trae párrafos. "
        "No lo reemplaces por filas de otros RUT.",
        f"Estudiante: {who} (student_id={int(student_id)}, ficha id={row.id}"
        + (f", actualizado={when}" if when else "")
        + ")",
    ]
    if lines:
        parts.append("\n".join(lines))
    else:
        parts.append(
            "La ficha existe, pero los campos narrativos están vacíos. "
            "No inventes evaluación que esta ficha no trae."
        )

    context = "\n\n".join(parts).strip()
    return {
        "studentId": int(student_id),
        "evaluationId": int(row.id),
        "narrativeFieldCount": len(lines),
        "context": context,
        "source": "psychopedagogical_evaluation_info",
        "chars": len(context),
    }
