"""Respuestas de formularios dinámicos (psicopedagogía) para el contexto del agente."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.backend.db.models.pie_core import (
    DynamicFormModel,
    DynamicFormSubmissionModel,
    StudentModel,
)

_BRACKET_RE = re.compile(r"^(.+?):\s*\[(.+)\]\s*$", re.S)

_SCALE_HINT = (
    "PROHIBIDO copiar al Word las etiquetas LOGRADO, EN PROCESO o REQUIERE APOYO: "
    "tradúcelas a prosa profesional sobre el desempeño del estudiante."
)


def _parse_question(field: dict[str, Any]) -> tuple[str, str]:
    section = str(field.get("section") or "").strip()
    raw = str(field.get("question") or "").strip()
    if section:
        inner = re.match(r"^\[(.+)\]$", raw, re.S)
        return section, (inner.group(1).strip() if inner else raw) or "(Sin texto)"
    match = _BRACKET_RE.match(raw)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "", raw or "(Sin texto)"


def _format_answer_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v).strip() for v in value if str(v).strip())
    return str(value).strip()


def student_has_dynamic_form_answers(
    db: Session,
    *,
    student_id: int,
    school_id: int | None = None,
    period_year: int | None = None,
) -> bool:
    """True si el estudiante tiene al menos una respuesta en formularios dinámicos."""
    if not student_id or int(student_id) < 1:
        return False
    q = db.query(DynamicFormSubmissionModel.id).filter(
        DynamicFormSubmissionModel.student_id == int(student_id)
    )
    if period_year is not None:
        q = q.filter(DynamicFormSubmissionModel.period_year == int(period_year))
    if school_id is not None:
        q = q.filter(DynamicFormSubmissionModel.school_id == int(school_id))
    return q.first() is not None


def collect_dynamic_form_answers_payload(
    db: Session,
    *,
    student_id: int,
    student_name: str | None = None,
    student_rut: str | None = None,
    school_id: int | None = None,
    period_year: int | None = None,
) -> dict[str, Any] | None:
    """
    Datos estructurados de respuestas de formularios para MCP.
    None si no hay envíos.
    """
    block = build_dynamic_form_answers_block(
        db,
        student_id=student_id,
        student_name=student_name,
        student_rut=student_rut,
        school_id=school_id,
        period_year=period_year,
    )
    if not block:
        return None

    sid = int(student_id)
    resolved_school = school_id
    if resolved_school is None:
        student = db.query(StudentModel).filter(StudentModel.id == sid).first()
        if student and student.school_id:
            resolved_school = int(student.school_id)

    q = (
        db.query(DynamicFormSubmissionModel, DynamicFormModel)
        .join(
            DynamicFormModel,
            DynamicFormModel.id == DynamicFormSubmissionModel.dynamic_form_id,
        )
        .filter(DynamicFormSubmissionModel.student_id == sid)
        .filter(DynamicFormModel.deleted_date.is_(None))
    )
    if period_year is not None:
        q = q.filter(DynamicFormSubmissionModel.period_year == int(period_year))
    if resolved_school is not None:
        q = q.filter(DynamicFormModel.school_id == int(resolved_school))

    forms_out: list[dict[str, Any]] = []
    for sub, form in q.order_by(DynamicFormSubmissionModel.id.desc()).all():
        try:
            answers = json.loads(sub.answers_json) if sub.answers_json else {}
            if not isinstance(answers, dict):
                answers = {}
        except (json.JSONDecodeError, TypeError):
            answers = {}
        forms_out.append(
            {
                "formId": form.id,
                "formName": (form.name or "").strip() or f"Formulario #{form.id}",
                "submissionId": sub.id,
                "periodYear": sub.period_year or form.period_year,
                "answers": answers,
            }
        )

    return {
        "studentId": sid,
        "studentName": (student_name or "").strip() or None,
        "studentRut": (student_rut or "").strip() or None,
        "forms": forms_out,
        "context": block,
        "source": "dynamic_forms",
        "chars": len(block),
    }


def build_dynamic_form_answers_block(
    db: Session,
    *,
    student_id: int,
    student_name: str | None = None,
    student_rut: str | None = None,
    school_id: int | None = None,
    period_year: int | None = None,
) -> str:
    """
    Bloque de contexto con respuestas del formulario (Inf. Eval. Psicopedagógica → Formularios).
    Se usa cuando el Excel/Files del agente no trae la fila del estudiante.
    """
    if not student_id or int(student_id) < 1:
        return ""

    sid = int(student_id)
    resolved_school = school_id
    if resolved_school is None:
        student = db.query(StudentModel).filter(StudentModel.id == sid).first()
        if student and student.school_id:
            resolved_school = int(student.school_id)

    q = (
        db.query(DynamicFormSubmissionModel, DynamicFormModel)
        .join(
            DynamicFormModel,
            DynamicFormModel.id == DynamicFormSubmissionModel.dynamic_form_id,
        )
        .filter(DynamicFormSubmissionModel.student_id == sid)
        .filter(DynamicFormModel.deleted_date.is_(None))
    )
    if period_year is not None:
        q = q.filter(DynamicFormSubmissionModel.period_year == int(period_year))
    if resolved_school is not None:
        q = q.filter(DynamicFormModel.school_id == int(resolved_school))

    rows = q.order_by(DynamicFormSubmissionModel.id.desc()).all()
    if not rows:
        return ""

    who = (student_name or "").strip() or (student_rut or "").strip() or f"student_id={sid}"
    sections: list[str] = [
        "RESPUESTAS DEL FORMULARIO PIE360 (Inf. Eval. Psicopedagógica / Formularios). "
        "Si el Excel / Files del agente no trae el cuestionario de ESTE estudiante, "
        "USA ESTAS RESPUESTAS como fuente principal de observación en aula "
        "(origen MCP: get_student_psychopedagogical_form_answers). "
        f"{_SCALE_HINT}",
        f"Estudiante: {who} (student_id={sid})",
    ]

    for sub, form in rows:
        try:
            answers = json.loads(sub.answers_json) if sub.answers_json else {}
            if not isinstance(answers, dict):
                answers = {}
        except (json.JSONDecodeError, TypeError):
            answers = {}
        try:
            fields = json.loads(form.fields_json) if form.fields_json else []
            if not isinstance(fields, list):
                fields = []
        except (json.JSONDecodeError, TypeError):
            fields = []

        form_name = (form.name or "").strip() or f"Formulario #{form.id}"
        period = sub.period_year or form.period_year or "—"
        area = (getattr(sub, "specialty", None) or "").strip()
        who_resp = (getattr(sub, "respondent_name", None) or "").strip()
        meta = f"id={form.id}, período {period}"
        if area:
            meta += f", área={area}"
        if who_resp:
            meta += f", responde={who_resp}"
        sections.append(f"### Formulario: {form_name} ({meta})")

        field_by_id = {
            str(f.get("id")): f
            for f in fields
            if isinstance(f, dict) and f.get("id") is not None
        }
        lines: list[str] = []
        current_section = ""
        seen: set[str] = set()

        ordered_ids = [str(f.get("id")) for f in fields if isinstance(f, dict) and f.get("id") is not None]
        for fid in list(answers.keys()):
            sid_key = str(fid)
            if sid_key not in seen and sid_key not in field_by_id:
                ordered_ids.append(sid_key)

        for fid in ordered_ids:
            if fid in seen:
                continue
            seen.add(fid)
            value = _format_answer_value(answers.get(fid))
            if not value:
                continue
            field = field_by_id.get(fid) or {}
            domain, question = _parse_question(field if isinstance(field, dict) else {})
            if not question or question == "(Sin texto)":
                question = fid
            if domain and domain != current_section:
                current_section = domain
                lines.append(f"\nÁmbito: {domain}")
            lines.append(f"- {question}: {value}")

        if lines:
            sections.append("\n".join(lines).strip())
        else:
            sections.append("(Sin respuestas con valor en este envío.)")

    return "\n\n".join(sections).strip()
