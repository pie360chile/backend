"""Resolución de estudiante/documento para generación en chat Agents."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.backend.db.models.agents_documents import AgentDocumentTemplateModel
from app.backend.db.models.pie_core import SchoolModel, StudentModel, StudentPersonalInfoModel
from app.backend.utils.agents_familia_pie360 import (
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
    "genera el informe",
    "generar el informe",
    "genera el documento",
    "generar el documento",
    "genera el word",
    "generar el word",
    "genera el docx",
    "generar el docx",
    "genera un informe",
    "generar un informe",
    "genera un documento",
    "generar un documento",
    "realiza el informe",
    "realizar el informe",
    "realiza el documento",
    "realizar el documento",
    "realiza un informe",
    "realizar un informe",
    "realiza un documento",
    "realizar un documento",
    "elabora el informe",
    "elaborar el informe",
    "elabora el documento",
    "elaborar el documento",
    "redacta el informe",
    "redactar el informe",
    "redacta el documento",
    "redactar el documento",
    "escribe el informe",
    "escribir el informe",
    "escribe el documento",
    "escribir el documento",
    "crea el informe",
    "crear informe",
    "crear el informe",
    "completa el informe",
    "completar el informe",
    "completa el documento",
    "completar el documento",
    "finaliza el informe",
    "finalizar el informe",
    "emite el informe",
    "emitir el informe",
    "confecciona el informe",
    "confeccionar el informe",
    "arma el informe",
    "armar el informe",
    "produce el informe",
    "producir el informe",
    "exporta el informe",
    "exportar el informe",
    "exporta el documento",
    "exportar el documento",
    "descarga el informe",
    "descargar el informe",
    "descarga el documento",
    "descargar el documento",
    "necesito el informe",
    "necesito el documento",
    "quiero el informe",
    "quiero el documento",
    "entrega el informe",
    "entregar el informe",
    "haz el informe",
    "hacer el informe",
    "haz el documento",
    "hacer el documento",
    "prepara el informe",
    "preparar el informe",
    "prepara el documento",
    "preparar el documento",
    "deja listo el informe",
    "dejar listo el informe",
    "genera de nuevo",
    "generar de nuevo",
    "realiza de nuevo",
    "realizar de nuevo",
    "vuelve a generar",
    "vuelve a realizar",
    "regenera el informe",
    "regenerar el informe",
)

# Verbo de acción + informe/documento en cualquier parte del mensaje
_GENERATION_PHRASE_RE = re.compile(
    r"\b("
    r"genera(r)?|realiza(r)?|elabora(r)?|redacta(r)?|escribe(r)?|crea(r)?|"
    r"completa(r)?|finaliza(r)?|emite(r)?|confecciona(r)?|arma(r)?|produce(r)?|"
    r"exporta(r)?|descarga(r)?|prepara(r)?|regenera(r)?|"
    r"haz|hacer|entrega(r)?"
    r")\s+(el\s+|un\s+|la\s+)?(informe|documento|word|docx)\b",
    re.IGNORECASE,
)

# Imperativo al inicio del mensaje (p. ej. «realiza informe familia isabella»)
_GENERATION_START_RE = re.compile(
    r"^\s*("
    r"genera|generar|realiza|realizar|elabora|elaborar|redacta|redactar|"
    r"escribe|escribir|crea|crear|completa|completar|finaliza|finalizar|"
    r"emite|emitir|confecciona|confeccionar|arma|armar|produce|producir|"
    r"exporta|exportar|descarga|descargar|prepara|preparar|"
    r"regenera|regenerar|haz|hacer|entrega|entregar"
    r")\b",
    re.IGNORECASE,
)

_SHORT_NON_GENERATION = frozenset(
    {
        "ok",
        "okay",
        "gracias",
        "thanks",
        "sí",
        "si",
        "no",
        "hola",
        "bueno",
        "perfecto",
        "listo",
        "entendido",
        "de acuerdo",
        "vale",
    }
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
    """
    True solo si el mensaje ACTUAL del usuario pide generar el Word.
    No usa historial: evita regenerar en cada turno tras un «genera el informe» previo
    o por palabras del asistente («informe», «genera», etc.) en mensajes anteriores.
    """
    del history  # compatibilidad API; la intención se evalúa solo en el turno actual
    text = (message or "").strip()
    if not text:
        return False
    low = text.lower()
    if low in _SHORT_NON_GENERATION:
        return False
    if any(hint in low for hint in _GENERATION_HINTS):
        return True
    if _GENERATION_PHRASE_RE.search(text):
        return True
    if _GENERATION_START_RE.match(text):
        return True
    return False


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


_NAME_NOISE = {
    "haz",
    "hacer",
    "genera",
    "generar",
    "completa",
    "completar",
    "informe",
    "documento",
    "familia",
    "estudiante",
    "alumna",
    "alumno",
    "de",
    "del",
    "la",
    "el",
    "los",
    "las",
    "un",
    "una",
    "por",
    "favor",
    "necesito",
    "quiero",
    "puedes",
    "con",
    "para",
    "word",
    "docx",
    "pdf",
}


def _fold_name(value: str) -> str:
    raw = (value or "").lower()
    for src, dst in (
        ("á", "a"),
        ("é", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ú", "u"),
        ("ü", "u"),
        ("ñ", "n"),
    ):
        raw = raw.replace(src, dst)
    return re.sub(r"[^a-z0-9\s]", " ", raw)


def extract_name_tokens_from_text(text: str) -> list[str]:
    folded = _fold_name(text or "")
    tokens = [t for t in folded.split() if len(t) >= 3 and t not in _NAME_NOISE]
    return tokens[:6]


def lookup_student_id_by_name(
    db: Session,
    name_text: str,
    *,
    customer_id: int | None = None,
    school_id: int | None = None,
) -> int | None:
    """Busca estudiante por nombre/apellido. Solo si hay un match claramente mejor."""
    tokens = extract_name_tokens_from_text(name_text)
    if len(tokens) < 2:
        return None

    q = db.query(StudentPersonalInfoModel, StudentModel).join(
        StudentModel, StudentModel.id == StudentPersonalInfoModel.student_id
    )
    if school_id:
        q = q.filter(StudentModel.school_id == int(school_id))
    elif customer_id:
        q = q.join(SchoolModel, SchoolModel.id == StudentModel.school_id).filter(
            SchoolModel.customer_id == int(customer_id)
        )

    scored: list[tuple[int, int]] = []
    for personal, _student in q.all():
        names = _fold_name(personal.names or "")
        father = _fold_name(personal.father_lastname or "")
        mother = _fold_name(personal.mother_lastname or "")
        social = _fold_name(personal.social_name or "")
        blob = f"{names} {father} {mother} {social}".strip()
        if not all(t in blob for t in tokens):
            continue

        name_parts = names.split()
        father_parts = father.split()
        mother_parts = mother.split()
        score = 0
        for t in tokens:
            if t in father_parts:
                score += 10
            elif t in mother_parts:
                score += 8
            elif name_parts and name_parts[0] == t:
                score += 6
            elif t in name_parts:
                score += 3
            elif t in social.split():
                score += 2
            else:
                score += 1
        scored.append((score, int(personal.student_id)))

    if not scored:
        return None
    scored.sort(key=lambda x: (-x[0], x[1]))
    best_score, best_id = scored[0]
    # Empate en el mejor puntaje → ambiguo.
    if len(scored) > 1 and scored[1][0] == best_score:
        return None
    return best_id


def resolve_student_id(
    db: Session,
    *,
    student_id: int | None,
    student_rut: str | None,
    message: str,
    history: list[dict[str, str]] | None,
    customer_id: int | None = None,
    school_id: int | None = None,
) -> tuple[int | None, str | None, str | None]:
    """
    Returns (student_id, rut_used, issue).
    Identificación firme: solo student_id (ficha) o RUT (no por nombre).
    issue: None | 'needs_rut' | 'not_found'
    """
    del customer_id, school_id
    if student_id:
        return student_id, None, None

    rut_raw = extract_rut_from_conversation(message, history, student_rut)
    if not rut_raw:
        return None, None, "needs_rut"

    found = lookup_student_id_by_rut(db, rut_raw)
    if found is None:
        return None, rut_raw, "not_found"
    return found, rut_raw, None


def build_ask_rut_reply(message: str) -> str:
    """Pide el RUT antes de generar el documento."""
    tokens = extract_name_tokens_from_text(message or "")
    name_bit = ""
    if tokens:
        pretty = " ".join(t.capitalize() for t in tokens)
        name_bit = f" (mencionaste a {pretty})"

    return (
        f"Para identificar bien al estudiante{name_bit} y generar el Informe a la Familia "
        "con todos los datos correctos, indícame el **RUT** con dígito verificador "
        "(por ejemplo `12.345.678-9`).\n\n"
        "Cuando lo envíes, continúo con la redacción detallada y la generación del documento. "
        "También puedes abrir el chat desde la ficha del estudiante."
    )


def infer_document_id(
    db: Session,
    agent_id: str,
    message: str,
    history: list[dict[str, str]] | None,
) -> int | None:
    rows = (
        db.query(AgentDocumentTemplateModel)
        .filter(AgentDocumentTemplateModel.agent_id == agent_id)
        .order_by(AgentDocumentTemplateModel.document_name.asc())
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
