"""Selección de archivos del agente relevantes para cada consulta."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from sqlalchemy.orm import Session

from app.backend.db.models import AgentFileModel
from app.backend.utils.agent_familia_template import (
    familia_form_template_priority,
    is_familia_form_file,
    is_familia_tabla_file,
    is_familia_tabla_template,
)
from app.backend.utils.agent_files import agent_dir

_TEMPLATE_HINTS = (
    "formato",
    "cartilla",
    "plantilla",
    "modelo",
    "informe_evaluacion",
    "informe_evaluaci",
    "informe de familia",
    "family_report",
    "informe_familia",
    "informe_familiar",
)

_TEMPLATE_PRIORITY = (
    "formato",
    "cartilla",
    "informe de familia",
    "plantilla",
    "modelo",
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


def _message_intent(message: str) -> str:
    """familia | evaluacion | general"""
    norm = _normalize(message)
    if "familia" in norm:
        return "familia"
    if "psicopedagog" in norm or "evaluacion" in norm or "evaluaci" in norm:
        return "evaluacion"
    return "general"


def _template_priority(display_name: str, intent: str = "general") -> int:
    lower = _normalize(display_name.replace("_", " ").replace("-", " "))
    if intent == "familia":
        if is_familia_form_template(display_name):
            return familia_form_template_priority(display_name)
        if "cartilla" in lower:
            return 2
        if is_familia_tabla_template(display_name):
            return 10
    elif intent == "evaluacion":
        if "cartilla" in lower:
            return 0
        if "formato" in lower and "evaluaci" in lower:
            return 1
        if "familia" in lower:
            return 50
    for index, hint in enumerate(_TEMPLATE_PRIORITY):
        if hint in lower:
            return index
    return len(_TEMPLATE_PRIORITY)


def _pick_template_rows(
    rows: list[AgentFileModel],
    limit: int,
    *,
    intent: str = "general",
    agent_id: str | None = None,
) -> list[AgentFileModel]:
    templates = [row for row in rows if _is_template_file(row.display_name)]

    def _disk_path(row: AgentFileModel) -> Path | None:
        if not agent_id:
            return None
        return agent_dir(agent_id) / row.id

    if intent == "familia":
        form_templates = [
            row
            for row in templates
            if is_familia_form_file(row.display_name, _disk_path(row))
        ]
        if form_templates:
            templates = form_templates
            limit = 1
        else:
            templates = [
                row
                for row in templates
                if is_familia_tabla_file(row.display_name, _disk_path(row))
                or "cartilla" in _normalize(row.display_name)
            ]
    templates.sort(
        key=lambda row: (_template_priority(row.display_name, intent), row.uploaded_at or 0)
    )
    return templates[:limit]


def _is_single_student_query(tokens: list[str]) -> bool:
    return len(tokens) >= 2


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

    tokens = _message_name_tokens(message)
    intent = _message_intent(message)
    single_student = _is_single_student_query(tokens)
    if single_student:
        max_files = min(max_files, 5)
    max_templates = 3 if intent == "familia" else (2 if single_student else 3)

    hit_file_ids = {hit["fileId"] for hit in (knowledge_hits or []) if hit.get("fileId")}
    if single_student and hit_file_ids:
        hit_file_ids = {
            row.id
            for row in rows
            if row.id in hit_file_ids and _file_name_matches_tokens(row.display_name, tokens)
        }

    selected: list[AgentFileModel] = []
    selected_ids: set[str] = set()

    def add(row: AgentFileModel) -> None:
        if row.id in selected_ids:
            return
        selected.append(row)
        selected_ids.add(row.id)

    for row in _pick_template_rows(rows, max_templates, intent=intent, agent_id=agent_id):
        add(row)

    for row in rows:
        if _file_name_matches_tokens(row.display_name, tokens):
            add(row)

    for row in rows:
        if row.id in hit_file_ids:
            add(row)

    if not selected:
        return rows[:max_files]

    if intent == "familia" and any(
        is_familia_form_file(r.display_name, agent_dir(agent_id) / r.id) for r in rows
    ):
        selected = [
            r
            for r in selected
            if not is_familia_tabla_file(r.display_name, agent_dir(agent_id) / r.id)
        ]

    if len(selected) > max_files:
        templates = [r for r in selected if _is_template_file(r.display_name)]
        others = [r for r in selected if not _is_template_file(r.display_name)]
        selected = (templates + others)[:max_files]

    return selected
