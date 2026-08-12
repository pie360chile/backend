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
    "hazme el informe",
    "hazme el documento",
    "dame el informe",
    "dame el documento",
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
    r"haz(me)?|hacer|dame|entrega(r)?"
    r")\s+(el\s+|un\s+|la\s+|los\s+)?(informe|informes|documento|documentos|word|docx)\b",
    re.IGNORECASE,
)

# Imperativo al inicio del mensaje (p. ej. «realiza informe familia isabella»)
_GENERATION_START_RE = re.compile(
    r"^\s*("
    r"genera|generar|realiza|realizar|elabora|elaborar|redacta|redactar|"
    r"escribe|escribir|crea|crear|completa|completar|finaliza|finalizar|"
    r"emite|emitir|confecciona|confeccionar|arma|armar|produce|producir|"
    r"exporta|exportar|descarga|descargar|prepara|preparar|"
    r"regenera|regenerar|hazme|haz|hacer|dame|entrega|entregar"
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
    "hazme",
    "hacer",
    "dame",
    "deme",
    "genera",
    "generame",
    "generar",
    "completa",
    "completar",
    "redacta",
    "redactar",
    "elabora",
    "elaborar",
    "realiza",
    "realizar",
    "escribe",
    "escribir",
    "crea",
    "crear",
    "emite",
    "emitir",
    "prepara",
    "preparar",
    "informe",
    "informde",
    "informes",
    "documento",
    "documentos",
    "familia",
    "psicopedagogico",
    "psicopedagogica",
    "psicopedagogico",
    "estudiante",
    "estudiantes",
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
    "puede",
    "con",
    "para",
    "word",
    "docx",
    "pdf",
    "todos",
    "todas",
    "datos",
    "correctos",
    "rut",
    "ficha",
    "chat",
    "ahora",
    "nuevo",
    "nueva",
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
    tokens = [
        t
        for t in folded.split()
        if len(t) >= 3 and t not in _NAME_NOISE and not t.startswith("inform")
    ]
    return tokens[:8]


def _score_students_by_name(
    db: Session,
    tokens: list[str],
    *,
    customer_id: int | None = None,
    school_id: int | None = None,
    period_year: int | None = None,
) -> int | None:
    q = db.query(StudentPersonalInfoModel, StudentModel).join(
        StudentModel, StudentModel.id == StudentPersonalInfoModel.student_id
    )
    try:
        q = q.filter(StudentModel.deleted_status_id == 0)
    except Exception:
        pass
    if school_id:
        q = q.filter(StudentModel.school_id == int(school_id))
    elif customer_id:
        q = q.join(SchoolModel, SchoolModel.id == StudentModel.school_id).filter(
            SchoolModel.customer_id == int(customer_id)
        )

    scored: list[tuple[int, int]] = []
    year_s = str(int(period_year)) if period_year else None
    for personal, student in q.all():
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
        if year_s and str(getattr(student, "period_year", "") or "") == year_s:
            score += 4
        scored.append((score, int(personal.student_id)))

    if not scored:
        return None
    scored.sort(key=lambda x: (-x[0], x[1]))
    best_score, best_id = scored[0]
    if len(scored) > 1 and scored[1][0] == best_score:
        return None
    return best_id


def lookup_student_id_by_name(
    db: Session,
    name_text: str,
    *,
    customer_id: int | None = None,
    school_id: int | None = None,
    period_year: int | None = None,
) -> int | None:
    """Busca estudiante por nombre/apellido. Solo si hay un match claramente mejor."""
    tokens = extract_name_tokens_from_text(name_text)
    if len(tokens) < 2:
        return None

    found = None
    if school_id:
        found = _score_students_by_name(
            db, tokens, school_id=int(school_id), period_year=period_year
        )
    if found:
        return found
    if customer_id:
        return _score_students_by_name(
            db, tokens, customer_id=int(customer_id), period_year=period_year
        )
    if not school_id:
        return _score_students_by_name(db, tokens, period_year=period_year)
    return None


def resolve_student_id(
    db: Session,
    *,
    student_id: int | None,
    student_rut: str | None,
    message: str,
    history: list[dict[str, str]] | None,
    customer_id: int | None = None,
    school_id: int | None = None,
    period_year: int | None = None,
) -> tuple[int | None, str | None, str | None]:
    """
    Returns (student_id, rut_used, issue).
    Prioridad: ficha (student_id) → RUT → nombre único en el cliente/sede.
    issue: None | 'needs_rut' | 'not_found'
    """
    if student_id:
        return student_id, None, None

    rut_raw = extract_rut_from_conversation(message, history, student_rut)
    if rut_raw:
        found = lookup_student_id_by_rut(db, rut_raw)
        if found is None:
            return None, rut_raw, "not_found"
        return found, rut_raw, None

    name_text = (message or "").strip() or conversation_blob(message, history)
    by_name = lookup_student_id_by_name(
        db,
        name_text,
        customer_id=customer_id,
        school_id=school_id,
        period_year=period_year,
    )
    if by_name:
        return by_name, None, None
    return None, None, "needs_rut"


def _document_label(document_id: int | None, agent_name: str | None = None) -> str:
    doc = int(document_id) if document_id is not None else None
    aname = (agent_name or "").lower()
    if doc == 27 or "psicoped" in aname:
        return "el Informe de Evaluación Psicopedagógica"
    if doc == 7 or "familia" in aname:
        return "el Informe a la Familia"
    return "el informe"


def build_ask_rut_reply(
    message: str,
    document_id: int | None = None,
    agent_name: str | None = None,
) -> str:
    """Pide el RUT antes de generar el documento."""
    tokens = extract_name_tokens_from_text(message or "")
    name_bit = ""
    if tokens:
        pretty = " ".join(t.capitalize() for t in tokens)
        name_bit = f" (mencionaste a {pretty})"
    label = _document_label(document_id, agent_name)

    return (
        f"Para identificar bien al estudiante{name_bit} y generar {label} "
        "con todos los datos correctos, indícame el **RUT** con dígito verificador "
        "(por ejemplo `12.345.678-9`).\n\n"
        "Cuando lo envíes, continúo con la redacción detallada y la generación del documento. "
        "También puedes abrir el chat desde la ficha del estudiante."
    )


def agent_template_document_ids(db: Session, agent_id: str) -> list[int]:
    rows = (
        db.query(AgentDocumentTemplateModel.document_id)
        .filter(AgentDocumentTemplateModel.agent_id == agent_id)
        .order_by(AgentDocumentTemplateModel.document_name.asc())
        .all()
    )
    return [int(r[0]) for r in rows]


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
            if "psicoped" in (row.document_name or "").lower() or int(row.document_id) == 27:
                return int(row.document_id)
    return None


def resolve_document_id_for_agent(
    db: Session,
    *,
    agent_id: str,
    agent_name: str | None,
    requested_document_id: int | None,
    message: str,
    history: list[dict[str, str]] | None,
) -> int | None:
    """
    El tipo de documento lo define el AGENTE (su plantilla), no la URL de otra ficha.
    Si la URL trae document_id=7 pero el agente es psicopedagógico, se usa 27.
    """
    template_ids = agent_template_document_ids(db, agent_id)
    if len(template_ids) == 1:
        return template_ids[0]

    requested = int(requested_document_id) if requested_document_id else None
    if requested and requested in template_ids:
        return requested

    inferred = infer_document_id(db, agent_id, message, history)
    if inferred:
        return inferred

    aname = (agent_name or "").lower()
    if "psicoped" in aname:
        return 27
    if "familia" in aname:
        return 7
    if requested and not template_ids:
        return requested
    return template_ids[0] if template_ids else requested


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

    pie = build_familia_pie360_context(db, student_id)
    school = (pie.get("student_school") or "").strip()
    course = (pie.get("student_course") or "").strip()
    age = (pie.get("student_age") or "").strip()
    if school:
        parts.append(f"Establecimiento (PIE360): {school}")
    if course:
        parts.append(f"Curso (PIE360): {course}")
    if age:
        parts.append(f"Edad (PIE360): {age}")
    try:
        from app.backend.classes.student_class import StudentClass

        got = StudentClass(db).get(student_id)
        academic = ((got or {}).get("student_data") or {}).get("academic_info") or {}
        nee = (academic.get("special_educational_need_name") or "").strip()
        if nee:
            parts.append(f"NEE (PIE360): {nee}")
    except Exception:
        pass
    parts.extend(familia_pie360_hint_lines(pie))
    parts.append(
        "DATOS DEL SISTEMA PIE360: si el cuestionario o Files no traen identificación, "
        "curso, establecimiento, NEE, profesional o apoderado, usa estos datos "
        "(equivalente a consultar la ficha / MCP). No los dejes en blanco."
    )

    return ". ".join(parts) + "."
