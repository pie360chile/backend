"""Resolución de estudiante/documento para generación en chat Agent v2."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.backend.db.models.agent_v2_documents import AgentV2DocumentTemplateModel
from app.backend.db.models.pie_core import StudentPersonalInfoModel
from app.backend.utils.agent_v2_familia_pie360 import (
    FAMILIA_DOCUMENT_ID,
    build_familia_pie360_context,
    familia_pie360_hint_lines,
    is_familia_document,
)

_RUT_RE = re.compile(
    r"\b(\d{1,2}[.\s]?\d{3}[.\s]?\d{3}[-\s]?[\dkK]|\d{7,8}[-\s]?[\dkK])\b",
    re.IGNORECASE,
)

_GENERATION_HINTS = (
    "genera",
    "generar",
    "elabora",
    "elaborar",
    "redacta",
    "redactar",
    "crea el informe",
    "crear informe",
    "informe para",
    "informe de",
    "informe a la",
)

_FAMILY_HINTS = (
    "informe para la familia",
    "informe a la familia",
    "informe de familia",
    "informe familia",
    "informe para la familia",
)

_PSICOPED_HINTS = ("psicopedag", "psicoped")


def normalize_rut(value: str) -> str:
    cleaned = re.sub(r"[^0-9kK]", "", (value or "").strip()).upper()
    return cleaned


def extract_rut_from_text(text: str) -> str | None:
    if not text:
        return None
    match = _RUT_RE.search(text)
    return match.group(1).strip() if match else None


def extract_rut_from_conversation(
    message: str,
    history: list[dict[str, str]] | None = None,
    explicit_rut: str | None = None,
) -> str | None:
    if explicit_rut and explicit_rut.strip():
        return explicit_rut.strip()
    found = extract_rut_from_text(message)
    if found:
        return found
    for item in reversed(history or []):
        if item.get("role") != "user":
            continue
        found = extract_rut_from_text(item.get("content") or "")
        if found:
            return found
    return None


def conversation_blob(message: str, history: list[dict[str, str]] | None = None) -> str:
    parts = [message or ""]
    for item in history or []:
        parts.append(item.get("content") or "")
    return "\n".join(parts)


def wants_document_generation(message: str, history: list[dict[str, str]] | None = None) -> bool:
    blob = conversation_blob(message, history).lower()
    return any(hint in blob for hint in _GENERATION_HINTS)


def lookup_student_id_by_rut(db: Session, rut: str) -> int | None:
    target = normalize_rut(rut)
    if len(target) < 2:
        return None
    rows = (
        db.query(StudentPersonalInfoModel.student_id, StudentPersonalInfoModel.identification_number)
        .filter(StudentPersonalInfoModel.identification_number.isnot(None))
        .filter(StudentPersonalInfoModel.identification_number != "")
        .all()
    )
    for student_id, identification in rows:
        if normalize_rut(identification or "") == target:
            return int(student_id)
    return None


def resolve_student_id(
    db: Session,
    *,
    student_id: int | None,
    student_rut: str | None,
    message: str,
    history: list[dict[str, str]] | None,
) -> tuple[int | None, str | None, str | None]:
    """
    Returns (student_id, rut_used, issue).
    issue: None | 'needs_rut' | 'not_found'
    """
    if student_id:
        return student_id, None, None

    rut_raw = extract_rut_from_conversation(message, history, student_rut)
    if not rut_raw:
        return None, None, "needs_rut"

    found = lookup_student_id_by_rut(db, rut_raw)
    if found is None:
        return None, rut_raw, "not_found"
    return found, rut_raw, None


def infer_document_id(
    db: Session,
    agent_id: str,
    message: str,
    history: list[dict[str, str]] | None,
) -> int | None:
    rows = (
        db.query(AgentV2DocumentTemplateModel)
        .filter(AgentV2DocumentTemplateModel.agent_id == agent_id)
        .order_by(AgentV2DocumentTemplateModel.document_name.asc())
        .all()
    )
    if not rows:
        return None
    if len(rows) == 1:
        return int(rows[0].document_id)

    blob = conversation_blob(message, history).lower()
    if any(h in blob for h in _FAMILY_HINTS) or ("familia" in blob and "informe" in blob):
        for row in rows:
            name = (row.document_name or "").lower()
            if "familia" in name or int(row.document_id) == FAMILIA_DOCUMENT_ID:
                return int(row.document_id)
    if any(h in blob for h in _PSICOPED_HINTS):
        for row in rows:
            if "psicoped" in (row.document_name or "").lower():
                return int(row.document_id)
    if wants_document_generation(message, history):
        for row in rows:
            if "familia" in (row.document_name or "").lower():
                return int(row.document_id)
    return None


def student_identification_hint(
    db: Session,
    student_id: int,
    document_id: int | None = None,
) -> str:
    personal = (
        db.query(StudentPersonalInfoModel)
        .filter(StudentPersonalInfoModel.student_id == student_id)
        .first()
    )
    if not personal:
        return f"Estudiante identificado en PIE360 (id {student_id})."
    names = (personal.names or "").strip()
    father = (personal.father_lastname or "").strip()
    mother = (personal.mother_lastname or "").strip()
    full = f"{names} {father} {mother}".strip()
    rut = (personal.identification_number or "").strip()
    parts = [f"Estudiante en PIE360: {full or f'id {student_id}'}"]
    if rut:
        parts.append(f"RUT/IPE: {rut}")

    if is_familia_document(document_id):
        pie = build_familia_pie360_context(db, student_id)
        parts.extend(familia_pie360_hint_lines(pie))
        parts.append(
            "Para Informe a la Familia: si Files/Excel no traen apoderado o profesional, "
            "usa estos datos de ficha PIE360 como respaldo."
        )

    return ". ".join(parts) + "."
