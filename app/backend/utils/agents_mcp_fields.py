"""Extrae payload de campos desde la respuesta del LLM para create_document."""

from __future__ import annotations

import json
import re
from typing import Any


_FENCE_RE = re.compile(
    r"```(?:json)?\s*(\{[\s\S]*?\})\s*```",
    re.IGNORECASE,
)


def extract_fields_from_reply(reply: str) -> dict[str, Any] | None:
    """
    Busca un objeto JSON con clave 'fields' (o el objeto plano de campos)
    en bloques ```json``` o en el último {...} del texto.
    """
    text = (reply or "").strip()
    if not text:
        return None

    candidates: list[str] = []
    for match in _FENCE_RE.finditer(text):
        candidates.append(match.group(1))

    # Último objeto JSON balanceado aproximado
    start = text.rfind("{")
    if start >= 0:
        candidates.append(text[start:])

    for raw in candidates:
        parsed = _try_parse_fields(raw)
        if parsed:
            return parsed
    return None


def _try_parse_fields(raw: str) -> dict[str, Any] | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Truncar basura tras el cierre del objeto
        try:
            decoder = json.JSONDecoder()
            data, _ = decoder.raw_decode(raw.strip())
        except Exception:
            return None
    if not isinstance(data, dict):
        return None
    if isinstance(data.get("fields"), dict) and data["fields"]:
        return {str(k): ("" if v is None else v) for k, v in data["fields"].items()}
    # Objeto plano: excluir claves de control
    skip = {"agent_id", "customer_id", "student_id", "document_id", "meta", "ok"}
    fields = {
        str(k): ("" if v is None else v)
        for k, v in data.items()
        if str(k) not in skip and not isinstance(v, (dict, list))
    }
    return fields or None


def strip_fields_json_from_reply(reply: str) -> str:
    """Quita el bloque JSON de campos para dejar la redacción legible en el chat."""
    text = reply or ""
    # Bloques ```json ... ``` completos
    cleaned = _FENCE_RE.sub("", text)
    # Fence incompleto al final (mientras stream-ea o sin cierre)
    cleaned = re.sub(
        r"```(?:json)?\s*\{[\s\S]*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = cleaned.strip()
    # JSON suelto con "fields" al final
    if cleaned.rstrip().endswith("}"):
        start = cleaned.rfind("{")
        if start >= 0 and _try_parse_fields(cleaned[start:]):
            cleaned = cleaned[:start].rstrip()
    # Frases residuales que anuncian el JSON
    cleaned = re.sub(
        r"(?i)\n*(?:a continuación[,:]?\s*)?(?:el\s+)?bloque\s+json[^\n]*:?\s*$",
        "",
        cleaned,
    ).strip()
    cleaned = re.sub(
        r"(?i)\n*(?:aquí\s+el\s+json|json\s+con\s+los\s+campos)[^\n]*:?\s*$",
        "",
        cleaned,
    ).strip()
    return cleaned.strip() or (reply or "").strip()


# Campos de identificación / cabecera (no cuentan como contenido del informe).
_IDENTIFICATION_FIELD_HINTS = frozenset(
    {
        "full_name",
        "student_full_name",
        "student_name",
        "identification_number",
        "student_identification_number",
        "student_rut",
        "rut",
        "ipe",
        "born_date",
        "birth_date",
        "student_birth_date",
        "student_born_date",
        "age",
        "student_age",
        "course",
        "student_course",
        "school",
        "student_school",
        "professional_name",
        "professional_full_name",
        "professional_identification_number",
        "professional_job_position",
        "professional_phone_email",
        "professional_phone",
        "professional_email",
        "professional_role",
        "professional_delivered_date_inform",
        "person_name",
        "person_full_name",
        "receiver_full_name",
        "person_identification_number",
        "person_relation_student",
        "person_presence",
        "receiver_relationship",
        "receiver_presence_of",
        "person_phone",
        "receiver_phone",
        "person_email",
        "receiver_email",
        "evaluation_type",
        "evaluation_date",
        "evaluation_date_1",
        "evaluation_date_2",
        "evaluation_date_3",
        "evaluation_date_4",
        "evaluation_date_5",
        "evaluation_date_6",
    }
)


def _is_identification_field(key: str) -> bool:
    k = (key or "").strip().lower()
    if k in _IDENTIFICATION_FIELD_HINTS:
        return True
    if k.startswith("evaluation_date"):
        return True
    if any(
        token in k
        for token in (
            "full_name",
            "identification",
            "_rut",
            "born_date",
            "birth_date",
            "phone",
            "email",
            "course",
            "school",
            "professional_",
            "person_",
            "receiver_",
        )
    ) and not any(
        token in k
        for token in (
            "strength",
            "support",
            "diagnos",
            "instrument",
            "reason",
            "agreement",
            "collaborative",
            "home_",
            "pedagogical",
            "social",
            "health",
            "observation",
            "progress",
            "synthesis",
        )
    ):
        return True
    return False


def narrative_fields_filled(fields: dict[str, Any] | None) -> tuple[int, int]:
    """
    Cuenta (rellenos, totales) de campos que NO son solo identificación.
    Si no hay campos narrativos en el payload, totales=0.
    """
    if not fields:
        return 0, 0
    narrative_keys = [k for k in fields.keys() if not _is_identification_field(str(k))]
    if not narrative_keys:
        return 0, 0
    filled = sum(1 for k in narrative_keys if str(fields.get(k) or "").strip())
    return filled, len(narrative_keys)


def is_content_too_thin(fields: dict[str, Any] | None) -> bool:
    """True si solo hay datos personales / fechas o el narrativo quedó demasiado corto."""
    filled, total = narrative_fields_filled(fields)
    if total == 0:
        # Solo keys de identificación en el JSON
        return True
    if filled == 0 or (filled / total) < 0.25:
        return True
    narrative_keys = [k for k in fields.keys() if not _is_identification_field(str(k))]
    texts = [str(fields.get(k) or "").strip() for k in narrative_keys if str(fields.get(k) or "").strip()]
    if not texts:
        return True
    avg_len = sum(len(t) for t in texts) / len(texts)
    # ~1 frase muy corta; el informe a la familia debe ir en párrafos.
    return avg_len < 120
