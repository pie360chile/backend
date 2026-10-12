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
    ("social_name", "Nombre social"),
    ("age", "Edad"),
)


def _text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return str(value).strip()


def _join(*parts: str) -> str:
    return "\n\n".join(part for part in parts if part)


def _scale_rows(db: Session, evaluation_id: int):
    from app.backend.db.models.pie_core import PsychopedagogicalEvaluationScaleModel

    return (
        db.query(PsychopedagogicalEvaluationScaleModel)
        .filter(
            PsychopedagogicalEvaluationScaleModel.psychopedagogical_evaluation_info_id
            == int(evaluation_id)
        )
        .order_by(
            PsychopedagogicalEvaluationScaleModel.scale_type,
            PsychopedagogicalEvaluationScaleModel.indicator_number,
        )
        .all()
    )


def _scales_summary(rows: list[Any]) -> str:
    pedagogical: list[str] = []
    social: list[str] = []
    for row in rows:
        kind = str(getattr(row, "scale_type", "") or "").lower()
        number = getattr(row, "indicator_number", None)
        value = _text(getattr(row, "value", None))
        if number is None or not value:
            continue
        item = f"{int(number)}={value}"
        if "social" in kind or "comunica" in kind:
            social.append(item)
        else:
            pedagogical.append(item)
    lines: list[str] = []
    if pedagogical:
        lines.append("Escala pedagógica (indicador=valor): " + ", ".join(pedagogical))
    if social:
        lines.append("Escala social/comunicativa (indicador=valor): " + ", ".join(social))
    return "\n".join(lines)


def _quantitative_text(row: Any) -> str:
    from app.backend.utils.psychoped_cognitive_quantitative import (
        build_cognitive_quantitative_table_text,
        parse_evalua_psychoped_matrices,
    )

    try:
        parsed = parse_evalua_psychoped_matrices(
            {
                "cognitive_quantitative_matrix": getattr(row, "cognitive_quantitative_matrix", None),
                "cognitive_general_scales": getattr(row, "cognitive_general_scales", None),
            }
        )
    except (TypeError, ValueError):
        return ""
    if parsed is None:
        return ""
    return build_cognitive_quantitative_table_text(parsed)


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
    school_history = _text(getattr(row, "school_history_background", None))
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
    motor = _join(
        _text(getattr(row, "motor_analysis", None)),
        _text(getattr(row, "motor_synthesis", None)),
    )
    other = _text(getattr(row, "other_suggestions", None))
    out: dict[str, str] = {}
    if diagnosis:
        out["diagnostic"] = diagnosis
        out["diagnosis"] = diagnosis
    if instruments:
        out["applied_instruments"] = instruments
    reason = _join(school_history, conclusion)
    if reason:
        out["evaluation_reason"] = reason
    if cognitive:
        out["pedagogical_strengths"] = cognitive
        out["strengths_1"] = cognitive
    elif conclusion:
        out["pedagogical_strengths"] = conclusion
        out["strengths_1"] = conclusion
    if personal:
        out["social_affective_strengths"] = personal
        out["strengths_2"] = personal
        out["social_field_1"] = personal
    school_block = "\n\n".join(part for part in (school, classroom, to_student) if part)
    if school_block:
        out["collaborative_work"] = school_block
        out["school_family_agreements"] = school_block
        out["agreements_commitments"] = school_block
        out["agreements"] = school_block
        out["pedagogical_support_needs"] = school_block
        out["support_needs_1"] = school_block
    if to_family:
        out["home_based_description"] = to_family
        out["home_support"] = to_family
        out["supports"] = to_family
        out["social_affective_support_needs"] = to_family
        out["support_needs_2"] = to_family
    if motor:
        out["health_strengths"] = motor
        out["strengths_3"] = motor
    if other:
        out["health_support_needs"] = other
        out["support_needs_3"] = other
    elif motor:
        out["health_support_needs"] = motor
        out["support_needs_3"] = motor
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


def apply_saved_psychoped_to_report_replacements(
    db: Session,
    student_id: int,
    replacements: dict[str, str],
    period_year: int | None = None,
) -> dict[str, str]:
    """Completa el Word del psicopedagógico con lo que ya está en la ficha."""
    row = _latest_psychoped_row(db, int(student_id), period_year)
    if row is None:
        return replacements
    saved: dict[str, str] = {}
    for key in (
        "instruments_applied",
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
        "professional_specialty",
        "professional_identification_number",
        "professional_registration_number",
        "admission_type",
        "admission_type_other",
    ):
        text = _text(getattr(row, key, None))
        if text:
            saved[key] = text
    social_name = _text(getattr(row, "social_name", None))
    age = _text(getattr(row, "age", None))
    diagnosis = _text(getattr(row, "diagnosis", None))
    if social_name:
        saved["social_name"] = social_name
        saved["student_social_name"] = social_name
    if age:
        saved["age"] = age
        saved["student_age"] = age
    if diagnosis:
        saved["diagnosis"] = diagnosis
        saved["diagnostic"] = diagnosis
    evaluation_date = _text(getattr(row, "evaluation_date", None))
    issue_date = _text(getattr(row, "diagnosis_issue_date", None))
    if evaluation_date:
        saved["evaluation_date"] = evaluation_date
    if issue_date:
        saved["issue_date"] = issue_date
        saved["diagnosis_issue_date"] = issue_date
    quantitative = _quantitative_text(row)
    if quantitative:
        saved["ac"] = quantitative
    for scale in _scale_rows(db, int(row.id)):
        number = getattr(scale, "indicator_number", None)
        value = _text(getattr(scale, "value", None))
        if number is None or not value:
            continue
        n = int(number)
        if n < 1 or n > 10:
            continue
        kind = str(getattr(scale, "scale_type", "") or "").lower()
        if "social" in kind or "comunica" in kind:
            saved[f"social_communicative_scale_{n}"] = value
        else:
            saved[f"pedagogical_scale_{n}"] = value
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
    quantitative = _quantitative_text(row)
    if quantitative:
        lines.append(f"- Cuadro cuantitativo y escalas generales:\n{quantitative}")
    scales = _scales_summary(_scale_rows(db, int(row.id)))
    if scales:
        lines.append(f"- {scales}")

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
