"""Persist Agent v2 familia field text into family_reports (ficha admin)."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.backend.classes.family_report_class import FamilyReportClass
from app.backend.db.models import FolderModel

logger = logging.getLogger(__name__)

FAMILIA_DOCUMENT_TYPE_ID = 7


def _pick_text(replacements: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = replacements.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _normalize_evaluation_type(
    replacements: dict[str, str],
    student_context: dict[str, Any] | None = None,
) -> str | None:
    """MySQL ENUM('admission','revaluation') no acepta cadena vacía."""
    raw = _pick_text(replacements, "evaluation_type")
    if not raw and student_context:
        raw = str(student_context.get("evaluation_type") or "").strip()
    if not raw:
        return "admission"
    norm = raw.strip().lower()
    if norm in ("revaluation", "reevaluación", "reevaluacion", "reeval", "2"):
        return "revaluation"
    if norm in ("admission", "admisión", "admision", "ingreso", "1"):
        return "admission"
    return "admission"


def _parse_born_date_iso(value: str | None) -> str | None:
    if not value or not str(value).strip():
        return None
    raw = str(value).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            if fmt == "%d/%m/%Y":
                part = raw.split()[0]
                return datetime.strptime(part, fmt).strftime("%Y-%m-%d")
            return datetime.strptime(raw[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def build_family_report_store_payload(
    student_id: int,
    replacements: dict[str, str],
    student_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Mapea campos de plantilla lucIA → columnas family_reports."""
    ctx = student_context or {}
    born_raw = _pick_text(
        replacements,
        "student_born_date",
        "student_birth_date",
        "born_date",
        "birth_date",
    )

    payload: dict[str, Any] = {
        "student_id": student_id,
        "document_type_id": FAMILIA_DOCUMENT_TYPE_ID,
        "student_full_name": _pick_text(
            replacements, "student_full_name", "full_name", "student_name"
        )
        or str(ctx.get("student_fullname") or "").strip(),
        "student_identification_number": _pick_text(
            replacements,
            "student_identification_number",
            "identification_number",
            "student_rut",
            "rut",
        )
        or str(ctx.get("identification_number") or "").strip(),
        "student_social_name": _pick_text(replacements, "student_social_name", "social_name"),
        "student_born_date": _parse_born_date_iso(born_raw),
        "student_age": _pick_text(replacements, "student_age", "age"),
        "student_course": _pick_text(replacements, "student_course", "course"),
        "student_school": _pick_text(replacements, "student_school", "school"),
        "professional_identification_number": _pick_text(
            replacements, "professional_identification_number", "professional_rut"
        ),
        "professional_social_name": _pick_text(
            replacements, "professional_social_name", "professional_full_name", "professional_name"
        ),
        "professional_role": _pick_text(
            replacements, "professional_role", "professional_job_position"
        ),
        "professional_phone": _pick_text(replacements, "professional_phone", "ph"),
        "professional_email": _pick_text(replacements, "professional_email", "em"),
        "report_delivery_date": _parse_born_date_iso(
            _pick_text(
                replacements,
                "report_delivery_date",
                "professional_delivered_date_inform",
            )
        ),
        "receiver_full_name": _pick_text(
            replacements, "receiver_full_name", "person_full_name", "person_name"
        ),
        "receiver_identification_number": _pick_text(
            replacements, "person_identification_number", "receiver_identification_number"
        ),
        "receiver_social_name": _pick_text(replacements, "receiver_social_name", "person_social_name"),
        "receiver_phone": _pick_text(replacements, "receiver_phone", "person_phone"),
        "receiver_email": _pick_text(replacements, "receiver_email", "person_email"),
        "receiver_relationship": _pick_text(
            replacements, "receiver_relationship", "person_relation_student"
        ),
        "receiver_presence_of": _pick_text(
            replacements, "receiver_presence_of", "person_presence"
        ),
        "evaluation_type": _normalize_evaluation_type(replacements, ctx),
        "evaluation_date": _parse_born_date_iso(_pick_text(replacements, "evaluation_date")),
        "applied_instruments": _pick_text(replacements, "applied_instruments"),
        "diagnosis": _pick_text(replacements, "diagnosis", "diagnostic"),
        "pedagogical_strengths": _pick_text(
            replacements, "pedagogical_strengths", "pedagogical_field_1"
        ),
        "pedagogical_support_needs": _pick_text(
            replacements, "pedagogical_support_needs", "pedagogical_field_2"
        ),
        "social_affective_strengths": _pick_text(
            replacements, "social_affective_strengths", "social_field_1"
        ),
        "social_affective_support_needs": _pick_text(
            replacements, "social_affective_support_needs", "social_field_2"
        ),
        "health_strengths": _pick_text(replacements, "health_strengths", "strengths_3"),
        "health_support_needs": _pick_text(
            replacements, "health_support_needs", "support_needs_3"
        ),
        "collaborative_work": _pick_text(replacements, "collaborative_work"),
        "home_support": _pick_text(
            replacements, "home_support", "supports", "home_based_description"
        ),
        "agreements_commitments": _pick_text(
            replacements,
            "agreements_commitments",
            "agreements",
            "school_family_agreements",
        ),
        "evaluation_date_1": _parse_born_date_iso(
            _pick_text(replacements, "evaluation_date_1")
        ),
        "evaluation_date_2": _parse_born_date_iso(
            _pick_text(replacements, "evaluation_date_2")
        ),
        "evaluation_date_3": _parse_born_date_iso(
            _pick_text(replacements, "evaluation_date_3")
        ),
    }

    if ctx.get("professional_id"):
        payload["professional_id"] = ctx.get("professional_id")

    return payload


def persist_family_report_from_agent(
    db: Session,
    student_id: int,
    replacements: dict[str, str],
    student_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Guarda una fila en family_reports con el texto redactado por Agent v2."""
    payload = build_family_report_store_payload(student_id, replacements, student_context)
    result = FamilyReportClass(db).store(payload)
    if result.get("status") == "error":
        logger.warning("family_reports store failed student=%s: %s", student_id, result.get("message"))
    return result


def link_folder_to_family_report(
    db: Session,
    folder_id: int | None,
    family_report_id: int | None,
) -> None:
    if not folder_id or not family_report_id:
        return
    try:
        row = db.query(FolderModel).filter(FolderModel.id == folder_id).first()
        if row is None:
            return
        row.detail_id = int(family_report_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("link folder %s to family_report %s: %s", folder_id, family_report_id, exc)
