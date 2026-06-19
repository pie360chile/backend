"""Relleno determinístico de campos de identificación en informe familia (formulario)."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from app.backend.utils.agent_familia_template import docx_has_form_controls
from app.backend.utils.agent_files import agent_dir

logger = logging.getLogger(__name__)

_NARRATIVE_KEYS = (
    "evaluation_reason",
    "diagnosis",
    "diagnostic",
    "pedagogical_strengths",
    "pedagogical_support_needs",
    "social_affective_strengths",
    "social_affective_support_needs",
    "health_strengths",
    "health_support_needs",
    "collaborative_work",
    "home_based_description",
    "home_support",
    "school_family_agreements",
    "agreements_commitments",
    "strengths_1",
    "support_needs_1",
    "strengths_2",
    "support_needs_2",
    "strengths_3",
    "support_needs_3",
)


def build_familia_identification_replacements(context: dict[str, Any]) -> dict[str, str]:
    """Solo identificación, checkboxes de evaluación y fechas de seguimiento."""
    student_full = str(context.get("student_full_name") or "").strip()
    student_id = str(context.get("student_identification_number") or "").strip()
    student_born = str(context.get("student_born_date") or "").strip()
    student_age = str(context.get("student_age") or "").strip()
    student_course = str(context.get("student_course") or "").strip()
    student_school = str(context.get("student_school") or "").strip()
    student_social = str(context.get("student_social_name") or "").strip()

    professional_full = str(
        context.get("professional_social_name")
        or context.get("professional_full_name")
        or ""
    ).strip()
    professional_id = str(context.get("professional_identification_number") or "").strip()
    professional_role = str(context.get("professional_role") or "").strip()
    ph = str(context.get("professional_phone") or "").strip()
    em = str(context.get("professional_email") or "").strip()
    professional_contact = f"{ph} / {em}".strip(" / ") if (ph or em) else ""
    report_delivery = str(context.get("report_delivery_date") or "").strip()

    receiver_full = str(context.get("receiver_full_name") or "").strip()
    receiver_id = str(context.get("receiver_identification_number") or "").strip()
    receiver_relation = str(context.get("receiver_relationship") or "").strip()
    receiver_presence = str(context.get("receiver_presence_of") or "").strip()

    no_info = "No informado"

    replacements: dict[str, str] = {
        "student_full_name": student_full,
        "student_identification_number": student_id or no_info,
        "student_social_name": student_social or no_info,
        "student_birth_date": student_born,
        "student_born_date": student_born,
        "student_age": student_age,
        "student_course": student_course,
        "student_school": student_school,
        "RUN": student_id or no_info,
        "Nombres y Apellidos": student_full,
        "Nombre de identidad": student_full,
        "Fecha nacimiento": student_born,
        "Edad": student_age,
        "Curso / Nivel": student_course,
        "Curso": student_course,
        "Establecimiento": student_school,
        "professional_full_name": professional_full,
        "professional_social_name": professional_full,
        "professional_identification_number": professional_id or no_info,
        "professional_job_position": professional_role,
        "professional_role": professional_role,
        "professional_phone_email": professional_contact,
        "professional_phone": ph,
        "professional_email": em,
        "professional_delivered_date_inform": report_delivery,
        "report_delivery_date": report_delivery,
        "Nombre": professional_full,
        "Rut": professional_id or no_info,
        "Rol / cargo": professional_role,
        "Rol/cargo": professional_role,
        "Teléfono / E-mail de contacto": professional_contact,
        "Teléfono / E-mail": professional_contact,
        "Fecha entrega de informe": report_delivery,
        "Fecha entrega": report_delivery,
        "person_full_name": receiver_full or no_info,
        "person_identification_number": receiver_id or no_info,
        "person_relation_student": receiver_relation or no_info,
        "person_presence_of": receiver_presence,
        "receiver_full_name": receiver_full or no_info,
        "receiver_identification_number": receiver_id or no_info,
        "receiver_relationship": receiver_relation or no_info,
        "receiver_presence_of": receiver_presence,
        "receiver_phone": str(context.get("receiver_phone") or "").strip() or no_info,
        "receiver_email": str(context.get("receiver_email") or "").strip() or no_info,
        "Teléfono": str(context.get("receiver_phone") or "").strip(),
        "E-mail de contacto": str(context.get("receiver_email") or "").strip(),
        "Relación con el/la estudiante": receiver_relation or no_info,
        "Nombre social": student_social or no_info,
        "RUT / IPE": student_id or no_info,
        "Rut / Pasaporte": receiver_id or no_info,
    }

    eval_type = str(context.get("evaluation_type") or "").strip().lower()
    if eval_type in ("admission", "admisión", "ingreso", "1"):
        replacements["evaluation"] = "1"
        replacements["Evaluación de Ingreso"] = "x"
    elif eval_type in ("revaluation", "reevaluación", "2"):
        replacements["reevaluation"] = "1"

    for key in ("evaluation_date_1", "evaluation_date_2", "evaluation_date_3"):
        val = str(context.get(key) or "").strip()
        if val:
            replacements[key] = val

    return {k: v for k, v in replacements.items() if v}


def build_familia_form_replacements(context: dict[str, Any]) -> dict[str, str]:
    """Identificación + narrativa desde BD (informe guardado en admin)."""
    return _append_narrative_replacements(
        build_familia_identification_replacements(context), context
    )


def _append_narrative_replacements(
    replacements: dict[str, str], context: dict[str, Any]
) -> dict[str, str]:
    diagnostic = str(context.get("diagnosis") or context.get("diagnostic") or "").strip()
    if diagnostic:
        replacements["diagnostic"] = diagnostic
        replacements["diagnosis"] = diagnostic

    evaluation_reason = str(
        context.get("evaluation_reason") or context.get("applied_instruments") or ""
    ).strip()
    if evaluation_reason:
        replacements["evaluation_reason"] = evaluation_reason

    alias_map = {
        "pedagogical_strengths": ("strengths_1", "fortalezas_1"),
        "pedagogical_support_needs": ("support_needs_1", "necesidades_apoyo_1"),
        "social_affective_strengths": ("strengths_2", "fortalezas_2", "fortalezas_social_afectivo"),
        "social_affective_support_needs": (
            "support_needs_2",
            "necesidades_apoyo_2",
            "necesidades_social_afectivo",
        ),
        "health_strengths": ("strengths_3",),
        "health_support_needs": ("support_needs_3",),
        "collaborative_work": ("educational_supports_school",),
        "home_based_description": ("home_support",),
        "school_family_agreements": ("agreements_commitments",),
    }
    for key in _NARRATIVE_KEYS:
        val = str(context.get(key) or "").strip()
        if not val:
            continue
        replacements[key] = val
        for alias in alias_map.get(key, ()):
            replacements[alias] = val

    return {k: v for k, v in replacements.items() if v}


def postprocess_saved_familia_docx(
    agent_id: str,
    saved: list[dict[str, Any]],
    student_context: dict[str, Any] | None,
    *,
    form_template_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Corrige identificación en .docx generado usando fill_docx_form y datos de BD."""
    if not student_context or not saved:
        return saved

    entry = saved[0]
    file_id = entry.get("id")
    if not file_id:
        return saved

    path = agent_dir(agent_id) / file_id
    if path.suffix.lower() != ".docx":
        return saved

    if not path.is_file() and form_template_path and form_template_path.is_file():
        shutil.copy2(form_template_path, path)

    if not path.is_file():
        return saved

    if not docx_has_form_controls(path):
        if form_template_path and form_template_path.is_file():
            shutil.copy2(form_template_path, path)
            logger.info(
                "Informe familia: reemplazado formato tablas por plantilla formulario %s",
                form_template_path.name,
            )
        else:
            return saved

    try:
        from app.backend.classes.documents_class import DocumentsClass

        replacements = build_familia_identification_replacements(student_context)
        result = DocumentsClass.fill_docx_form(str(path), replacements, str(path))
        if result.get("status") == "error":
            logger.warning(
                "Prefill familia falló para %s: %s",
                path.name,
                result.get("message"),
            )
        else:
            logger.info("Prefill familia aplicado en %s", path.name)
    except Exception as exc:
        logger.warning("Prefill familia no aplicado en %s: %s", path.name, exc)

    return saved
