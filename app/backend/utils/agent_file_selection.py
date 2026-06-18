"""Selección de archivos del agente relevantes para cada consulta."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.backend.db.models import AgentFileModel

_TEMPLATE_HINTS = (
    "formato",
    "cartilla",
    "plantilla",
    "modelo",
    "informe_evaluacion",
    "informe_evaluaci",
    "informe de familia",
)

_STOPWORDS = {
    "para",
    "como",
    "este",
    "esta",
    "genera",
    "haz",
    "hacer",
    "informe",
    "informa",
    "familia",
    "estudiante",
    "alumna",
    "alumno",
    "documento",
    "archivo",
    "usando",
    "segun",
    "según",
    "con",
    "del",
    "de",
    "la",
    "el",
    "los",
    "las",
    "una",
    "uno",
    "por",
    "que",
    "psicopedagogico",
    "psicopedagógico",
    "evaluacion",
    "evaluación",
}


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    asciiish = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", asciiish.lower()).strip()


def _is_template_file(display_name: str) -> bool:
    lower = _normalize(display_name.replace("_", " ").replace("-", " "))
    return any(hint in lower for hint in _TEMPLATE_HINTS)


def _message_name_tokens(message: str) -> list[str]:
    tokens = [t for t in _normalize(message).split() if len(t) >= 3 and t not in _STOPWORDS]
    # Prioriza nombres propios (palabras más largas / menos comunes)
    return sorted(set(tokens), key=len, reverse=True)


def _file_name_matches_tokens(display_name: str, tokens: list[str]) -> bool:
    if not tokens:
        return False
    haystack = _normalize(Path(display_name).stem if "." in display_name else display_name)
    matched = 0
    for token in tokens:
        if len(token) < 3:
            continue
        if token in haystack:
            matched += 1
    # Con 2+ tokens (ej. isabella + diaz) exige al menos 2 coincidencias
    if len(tokens) >= 2:
        return matched >= 2
    return matched >= 1


def select_agent_file_rows(
    db: Session,
    agent_id: str,
    message: str,
    knowledge_hits: list[dict[str, Any]] | None = None,
    *,
    max_files: int = 8,
) -> list[AgentFileModel]:
    """Reduce archivos enviados a OpenAI: plantillas + estudiante/caso + hits de búsqueda."""
    rows = (
        db.query(AgentFileModel)
        .filter(AgentFileModel.agent_id == agent_id)
        .order_by(AgentFileModel.uploaded_at.asc())
        .all()
    )
    if not rows:
        return []

    if len(rows) <= max_files:
        return rows

    tokens = _message_name_tokens(message)
    hit_file_ids = {hit["fileId"] for hit in (knowledge_hits or []) if hit.get("fileId")}

    selected: list[AgentFileModel] = []
    selected_ids: set[str] = set()

    def add(row: AgentFileModel) -> None:
        if row.id in selected_ids:
            return
        selected.append(row)
        selected_ids.add(row.id)

    for row in rows:
        if _is_template_file(row.display_name):
            add(row)

    for row in rows:
        if row.id in hit_file_ids:
            add(row)

    for row in rows:
        if _file_name_matches_tokens(row.display_name, tokens):
            add(row)

    if not selected:
        return rows

    if len(selected) > max_files:
        # Plantillas primero, luego el resto por orden de subida
        templates = [r for r in selected if _is_template_file(r.display_name)]
        others = [r for r in selected if not _is_template_file(r.display_name)]
        selected = (templates + others)[:max_files]

    return selected
