"""Anamnesis + formulario del apoderado para la historia escolar del informe."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.backend.classes.anamnesis_class import AnamnesisClass
from app.backend.utils.agents_dynamic_form_context import build_dynamic_form_answers_block

_MODALITY = {
    "regular": "Regular",
    "especial": "Especial",
    "tecnica": "Técnica",
    "técnica": "Técnica",
}
_PERFORMANCE = {
    "satisfactorio": "Satisfactorio",
    "insatisfactorio": "Insatisfactorio",
}
_EXPECTATIONS = {
    "alta": "Alta (incluye al grupo familiar)",
    "mediana": "Mediana (incluye solo madre/padre)",
    "baja": "Baja (no incluye a ningún miembro)",
}
_ENVIRONMENT = {
    "ambos": "Adecuado en lo físico y en lo emocional",
    "fisico": "Solo adecuado en lo físico",
    "físico": "Solo adecuado en lo físico",
    "emocional": "Solo adecuado en lo emocional",
}

# Hechos de trayectoria y familia. No incluye pautas de desarrollo (motricidad, lenguaje, etc.).
_YES_NO_FACTS: tuple[tuple[str, str], ...] = (
    ("attended_kindergarten", "Asistió a jardín infantil"),
    ("repeated_grade", "Ha repetido curso"),
    ("learning_difficulty", "Dificultad de aprendizaje"),
    ("participation_difficulty", "Dificultad para participar"),
    ("disruptive_behavior", "Conducta disruptiva"),
    ("attends_regularly", "Asiste regularmente"),
    ("attends_gladly", "Asiste con agrado"),
    ("family_support_homework", "Apoyo familiar en las tareas"),
    ("friends", "Tiene amigos o amigas"),
)

_TEXT_FACTS: tuple[tuple[str, str], ...] = (
    ("current_schooling", "Escolaridad actual"),
    ("school_name", "Establecimiento informado en la anamnesis"),
    ("school_entry_age", "Edad de ingreso al sistema escolar"),
    ("schools_count", "Número de colegios en que ha estudiado"),
    ("changes_reason", "Motivo de los cambios de colegio"),
    ("repeated_courses", "Cursos repetidos"),
    ("repeated_reason", "Motivo de la repitencia"),
    ("current_level", "Nivel o curso actual"),
    ("family_attitude", "Actitud de la familia"),
    ("performance_reasons", "Motivos de la evaluación familiar del desempeño"),
    ("response_difficulties_other", "Otra respuesta ante dificultades"),
    ("response_success_other", "Otra respuesta ante éxitos"),
    ("rewards_other", "Otros refuerzos o premios"),
    ("supporters_other_professionals", "Otros profesionales que apoyan"),
    ("family_health_history", "Antecedentes de salud de la familia"),
    ("health_problems_treatment", "Control o tratamiento de problemas de salud (medicación si se indica)"),
    ("final_comments", "Comentarios u observaciones de la anamnesis"),
)

_LIST_FACTS: tuple[tuple[str, str], ...] = (
    ("response_difficulties", "Respuesta de la familia ante dificultades escolares"),
    ("response_success", "Respuesta de la familia ante éxitos escolares"),
    ("rewards", "Refuerzos o premios"),
    ("supporters", "Quiénes apoyan el proceso"),
)


def _yes_no(value: Any) -> str:
    try:
        code = int(value)
    except (TypeError, ValueError):
        return ""
    if code == 1:
        return "Sí"
    if code == 2:
        return "No"
    return ""


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                raw = item.get("value") or item.get("name") or ""
            else:
                raw = item
            text = str(raw).strip()
            if text:
                parts.append(text)
        return ", ".join(parts)
    if isinstance(value, dict):
        parts = []
        for key, raw in value.items():
            text = str(raw).strip() if raw is not None else ""
            if text:
                parts.append(f"{key}: {text}")
        return ", ".join(parts)
    return str(value).strip()


def _mapped(value: Any, table: dict[str, str]) -> str:
    text = _as_text(value)
    if not text:
        return ""
    return table.get(text.lower(), text)


def _line(label: str, value: str) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    return f"- {label}: {text}"


def _anamnesis_fact_lines(record: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, label in _YES_NO_FACTS:
        line = _line(label, _yes_no(record.get(key)))
        if line:
            lines.append(line)
    for key, label in _TEXT_FACTS:
        line = _line(label, _as_text(record.get(key)))
        if line:
            lines.append(line)
    modality = _line(
        "Modalidad de enseñanza",
        _mapped(record.get("teaching_modality"), _MODALITY),
    )
    if modality:
        lines.append(modality)
    performance = _line(
        "Cómo evalúa la familia el desempeño escolar",
        _mapped(record.get("performance_assessment"), _PERFORMANCE),
    )
    if performance:
        lines.append(performance)
    expectations = _line(
        "Expectativas de la familia",
        _mapped(record.get("expectations"), _EXPECTATIONS),
    )
    if expectations:
        lines.append(expectations)
    environment = _line(
        "Ambiente físico y emocional",
        _mapped(record.get("environment"), _ENVIRONMENT),
    )
    if environment:
        lines.append(environment)
    for key, label in _LIST_FACTS:
        line = _line(label, _as_text(record.get(key)))
        if line:
            lines.append(line)

    informants = record.get("informants") or []
    if isinstance(informants, list):
        names: list[str] = []
        for item in informants:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            relation = str(item.get("relationship") or "").strip()
            if name and relation:
                names.append(f"{name} ({relation})")
            elif name or relation:
                names.append(name or relation)
        if names:
            lines.append(f"- Informantes: {', '.join(names)}")
    return lines


def build_school_history_context(
    db: Session,
    *,
    student_id: int,
    student_name: str | None = None,
    student_rut: str | None = None,
    school_id: int | None = None,
    period_year: int | None = None,
) -> dict[str, Any] | None:
    """
    Contexto para redactar school_history_background.

    None si no hay anamnesis con hechos ni formulario del apoderado.
    """
    if not student_id or int(student_id) < 1:
        return None

    sid = int(student_id)
    record = AnamnesisClass(db).get_by_student_id(sid)
    anamnesis_found = isinstance(record, dict) and record.get("status") != "error"
    facts: list[str] = _anamnesis_fact_lines(record) if anamnesis_found else []

    guardian = build_dynamic_form_answers_block(
        db,
        student_id=sid,
        student_name=student_name,
        student_rut=student_rut,
        school_id=school_id,
        period_year=period_year,
        respondent_type_id=1,
        intro=(
            "RESPUESTAS DEL FORMULARIO DEL APODERADO. "
            "En la historia escolar usa solo las preguntas sobre trayectoria, jardín, "
            "repitencia, colegios, apoyos previos, hogar, tareas, intereses, descripción "
            "familiar o medicación. "
            "Las escalas de observación en aula (LOGRADO, EN PROCESO, REQUIERE APOYO, "
            "NO OBSERVADO) no son historia escolar: no las conviertas en ese apartado."
        ),
    )

    if not facts and not guardian:
        return None

    who = (student_name or "").strip() or (student_rut or "").strip() or f"student_id={sid}"
    parts = [
        "HISTORIA ESCOLAR Y ANTECEDENTES FAMILIARES. "
        "Fuente MCP: get_student_school_history. "
        "Sirve solo para redactar `school_history_background`. "
        "Redacta uno o dos párrafos: nombre, curso y establecimiento si constan en los datos; "
        "luego «De acuerdo con los antecedentes aportados por su familia, …». "
        "Integra únicamente los hechos de este bloque. "
        "Prohibido inventar jardín, escuela de lenguaje, repitencia, cantidad de colegios, "
        "apoyos, tareas, intereses, descripción familiar o medicación si aquí no aparecen. "
        "Si no hay hechos de trayectoria ni de familia, deja el campo vacío.",
        f"Estudiante: {who} (student_id={sid})",
    ]
    if facts:
        parts.append(
            "ANAMNESIS (última versión, antecedentes escolares y apoyo de la familia):\n"
            + "\n".join(facts)
        )
    else:
        parts.append("ANAMNESIS: no hay ficha de anamnesis con antecedentes escolares para este estudiante.")
    if guardian:
        parts.append(guardian)
    else:
        parts.append("FORMULARIO DEL APODERADO: no hay respuestas guardadas.")

    context = "\n\n".join(parts).strip()
    return {
        "studentId": sid,
        "studentName": (student_name or "").strip() or None,
        "studentRut": (student_rut or "").strip() or None,
        "anamnesisFound": anamnesis_found,
        "anamnesisId": record.get("id") if anamnesis_found else None,
        "schoolFactCount": len(facts),
        "guardianFormIncluded": bool(guardian),
        "context": context,
        "source": "anamnesis_and_guardian_form",
        "chars": len(context),
    }
