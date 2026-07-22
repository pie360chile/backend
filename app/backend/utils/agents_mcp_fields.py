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
    cleaned = _FENCE_RE.sub("", text).strip()
    # Si quedó un JSON suelto al final, recortar desde el último {
    if cleaned.rstrip().endswith("}"):
        # Solo si parsea como fields
        start = cleaned.rfind("{")
        if start >= 0 and _try_parse_fields(cleaned[start:]):
            cleaned = cleaned[:start].rstrip()
    return cleaned.strip() or (reply or "").strip()
