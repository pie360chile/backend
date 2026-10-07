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


def _latest_period_folder(db: Session, student_id: int, period_year: int | None):
    """Última carpeta del informe psicopedagógico (doc 27) del período."""
    from app.backend.db.models.pie_core import FolderModel

    rows = (
        db.query(FolderModel)
        .filter(FolderModel.student_id == int(student_id))
        .filter(FolderModel.document_id == 27)
        .filter(FolderModel.deleted_date.is_(None))
        .all()
    )
    if period_year is not None:
        wanted = str(int(period_year))
        rows = [row for row in rows if str(row.period_year or "").strip() == wanted]
    if not rows:
        return None

    def _year(row: Any) -> int:
        try:
            return int(str(row.period_year or "").strip() or 0)
        except ValueError:
            return 0

    return max(rows, key=lambda row: (_year(row), int(row.version_id or 0), int(row.id or 0)))


def _latest_psychoped_row(db: Session, student_id: int, period_year: int | None = None):
    """Ficha del período. Sin carpeta de ese año, no sirve un informe de otro período."""
    if int(student_id) < 1:
        return None
    folder = _latest_period_folder(db, int(student_id), period_year)
    if folder is None:
        return None
    if folder.detail_id:
        linked = (
            db.query(PsychopedagogicalEvaluationInfoModel)
            .filter(PsychopedagogicalEvaluationInfoModel.id == int(folder.detail_id))
            .filter(PsychopedagogicalEvaluationInfoModel.student_id == int(student_id))
            .first()
        )
        if linked is not None:
            return linked
    return (
        db.query(PsychopedagogicalEvaluationInfoModel)
        .filter(PsychopedagogicalEvaluationInfoModel.student_id == int(student_id))
        .order_by(PsychopedagogicalEvaluationInfoModel.id.desc())
        .first()
    )


def family_fields_from_saved_psychoped(
    db: Session,
    student_id: int,
    period_year: int | None = None,
) -> dict[str, str]:
    """Pasa al informe a la familia solo el texto ya guardado en la ficha del período."""
    row = _latest_psychoped_row(db, student_id, period_year)
    if row is None:
        return {}
    diagnosis = _text(getattr(row, "diagnosis", None))
    instruments = _text(getattr(row, "instruments_applied", None))
    conclusion = _text(getattr(row, "conclusion", None))
    school = _text(getattr(row, "suggestions_to_school", None))
    classroom = _text(getattr(row, "suggestions_to_classroom_team", None))
    to_student = _text(getattr(row, "suggestions_to_student", None))
    to_family = _text(getattr(row, "suggestions_to_family", None))
    cognitive = "\n\n".join(
        part
        for part in (
            _text(getattr(row, "cognitive_analysis", None)),
            _text(getattr(row, "cognitive_synthesis", None)),
        )
        if part
    )
    personal = "\n\n".join(
        part
        for part in (
            _text(getattr(row, "personal_analysis", None)),
            _text(getattr(row, "personal_synthesis", None)),
        )
        if part
    )
    out: dict[str, str] = {}
    if diagnosis:
        out["diagnostic"] = diagnosis
        out["diagnosis"] = diagnosis
    if instruments:
        out["applied_instruments"] = instruments
    if conclusion:
        out["evaluation_reason"] = conclusion
    if cognitive:
        out["pedagogical_strengths"] = cognitive
        out["strengths_1"] = cognitive
    elif conclusion:
        out["pedagogical_strengths"] = conclusion
        out["strengths_1"] = conclusion
    if personal:
        out["social_affective_strengths"] = personal
    school_block = "\n\n".join(part for part in (school, classroom, to_student) if part)
    if school_block:
        out["collaborative_work"] = school_block
        out["school_family_agreements"] = school_block
        out["agreements_commitments"] = school_block
    if to_family:
        out["home_based_description"] = to_family
        out["home_support"] = to_family
    return out


def apply_saved_psychoped_to_family_replacements(
    db: Session,
    student_id: int,
    replacements: dict[str, str],
    period_year: int | None = None,
) -> dict[str, str]:
    """Rellena los huecos del informe a la familia con el psicopedagógico del período."""
    saved = family_fields_from_saved_psychoped(db, int(student_id), period_year)
    for key, value in saved.items():
        if value and not str(replacements.get(key) or "").strip():
            replacements[key] = value
    return replacements


def student_has_usable_psychoped_report(
    db: Session,
    student_id: int,
    period_year: int | None = None,
) -> bool:
    """True solo si la ficha del período trae análisis, síntesis, conclusión o sugerencias."""
    row = _latest_psychoped_row(db, student_id, period_year)
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
    period_year: int | None = None,
) -> dict[str, Any] | None:
    """
    Última ficha psychopedagogical_evaluation_info del estudiante.

    None si no hay fila.
    """
    if not student_id or int(student_id) < 1:
        return None

    row = _latest_psychoped_row(db, int(student_id), period_year)
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
