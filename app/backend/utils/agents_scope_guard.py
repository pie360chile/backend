"""Los agentes solo atienden el ámbito PIE Chile."""

from __future__ import annotations

import re
import unicodedata

from app.backend.utils.agents_chat_context import (
    extract_name_tokens_from_text,
    extract_rut_from_text,
    wants_document_generation,
)

SCOPE_REJECT_REPLY = (
    "Solo puedo atender consultas del **PIE Chile** (Programa de Integración Escolar): "
    "informes psicopedagógicos, informes a la familia, estudiantes, NEE, Decreto 170 "
    "y la documentación del establecimiento en PIE360.\n\n"
    "Esa pregunta está fuera de ese ámbito, por lo que no puedo responderla. "
    "Si necesitas un informe o un dato de un estudiante del PIE, indícalo con el RUT "
    "o el nombre y continúo."
)

_PIE_TERMS = (
    "pie",
    "neep",
    "nee",
    "mineduc",
    "decreto",
    "inclusion",
    "inclusi",
    "informe",
    "psicoped",
    "familia",
    "estudiante",
    "alumno",
    "alumna",
    "rut",
    "cuestionario",
    "evaluacion",
    "anamnesis",
    "adecuacion",
    "aula",
    "curso",
    "colegio",
    "liceo",
    "establecimiento",
    "tea",
    "tda",
    "tdah",
    "dil",
    "dea",
    "fonoaudio",
    "ocupacional",
    "diferencial",
    "utp",
    "pai",
    "pia",
    "diagnostico",
    "observacion",
    "logrado",
    "apoderado",
    "ficha",
    "barrera",
    "documento",
    "word",
    "plantilla",
    "pauta",
    "especialista",
    "profesional",
    "mediacion",
    "apoyo",
    "sintesis",
    "sugerencia",
    "recomendacion",
    "campo",
    "narrativ",
    "reescrib",
    "redact",
    "analisis",
    "conclusion",
    "instrumento",
    "escala",
    "ingreso",
    "reevalu",
    "pie360",
    "integracion escolar",
)

# Palabras cortas o ambiguas: no bastan si el mensaje es claramente de otro tema.
_WEAK_PIE_TERMS = frozenset(
    {
        "pie",
        "word",
        "apoyo",
        "profesional",
        "campo",
        "escala",
        "aula",
        "curso",
        "documento",
        "redact",
        "reescrib",
    }
)

_OFF_TOPIC = (
    "clima",
    "receta",
    "futbol",
    "partido",
    "bitcoin",
    "crypto",
    "poema",
    "chiste",
    "traduce",
    "traduccion",
    "netflix",
    "pelicula",
    "cancion",
    "cocina",
    "viaje",
    "hotel",
    "capital de",
    "quien gano",
    "quien ganó",
    "horoscopo",
    "loteria",
    "videojuego",
    "minecraft",
    "whatsapp api",
    "javascript",
    "python",
    "programar",
    "programacion",
)

_SHORT_OK = {
    "ok",
    "okay",
    "gracias",
    "thanks",
    "si",
    "sí",
    "no",
    "hola",
    "buenos dias",
    "buenas tardes",
    "buenas noches",
    "bueno",
    "perfecto",
    "listo",
    "entendido",
    "de acuerdo",
    "vale",
    "continua",
    "continúa",
    "sigue",
}

_COURSE_HINT_RE = re.compile(
    r"\b(?:20\d{2}|[1-8]\s*(?:medio|basico|básico)|[1-8]°|[1-8]ro|"
    r"kinder|prekinder|[1-8]\s*[a-k]|curso\s+\S+)",
    re.IGNORECASE,
)

_QUESTION_RE = re.compile(
    r"^\s*(que|qué|como|cómo|por que|por qué|cual|cuál|quien|quién|donde|dónde|"
    r"cuando|cuándo|explica|explícame|dime|cuentame|cuéntame|busca|search|"
    r"what|who|where|when|why|how)\b",
    re.IGNORECASE,
)


def _fold(value: str) -> str:
    raw = unicodedata.normalize("NFKD", value or "")
    raw = "".join(c for c in raw if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", raw).strip()


def _has_term(folded: str, term: str) -> bool:
    if " " in term or len(term) >= 6:
        return term in folded
    if len(term) <= 4:
        return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", folded) is not None
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}", folded) is not None


def message_is_pie_chile_scope(text: str) -> bool:
    """True si el mensaje puede tratarse como consulta PIE Chile / informes."""
    raw = (text or "").strip()
    if not raw:
        return True
    folded = _fold(raw)
    if folded in _SHORT_OK:
        return True
    if extract_rut_from_text(raw):
        return True
    if len(folded) < 48 and _COURSE_HINT_RE.search(raw):
        return True
    strong = any(
        _has_term(folded, term) for term in _PIE_TERMS if term not in _WEAK_PIE_TERMS
    )
    if strong:
        return True
    if any(term in folded for term in _OFF_TOPIC):
        return False
    if any(_has_term(folded, term) for term in _WEAK_PIE_TERMS):
        return True
    if wants_document_generation(raw):
        return True
    if len(extract_name_tokens_from_text(raw)) >= 2 and not _QUESTION_RE.match(raw):
        return True
    return False


def message_is_off_topic(text: str) -> bool:
    """Fuera de PIE Chile: rechazar sin llamar al modelo."""
    return not message_is_pie_chile_scope(text)
