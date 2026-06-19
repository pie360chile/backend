"""Generación del informe familia: base PIE360 + redacción GPT."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.db.models import AgentResponseFileModel
from app.backend.utils.agent_familia_prefill import (
    build_familia_form_replacements,
    build_familia_identification_replacements,
)
from app.backend.utils.agent_familia_template import (
    docx_has_form_controls,
    resolve_form_template_path,
)
from app.backend.utils.agent_file_selection import _message_intent
from app.backend.utils.agent_files import agent_dir, build_response_storage_path, ensure_responses_dir

logger = logging.getLogger(__name__)


def _system_family_report_template() -> Path | None:
    path = Path(settings.files_dir) / "original_student_files" / "family_report.docx"
    if path.is_file() and docx_has_form_controls(path):
        return path
    return None


def resolve_form_template_for_generation(agent_id: str, selected_rows: list[Any]) -> Path | None:
    """Plantilla formulario del agente o, en su defecto, family_report.docx del sistema."""
    path = resolve_form_template_path(agent_id, selected_rows)
    if path and docx_has_form_controls(path):
        return path
    return _system_family_report_template()


def _safe_filename(student_name: str | None) -> str:
    base = re.sub(r"[^\w\s-]", "", (student_name or "estudiante")).strip().replace(" ", "_")
    return (base[:40] or "estudiante").strip("_")


def _fill_and_save(
    template_path: Path,
    out_path: Path,
    replacements: dict[str, str],
) -> None:
    from app.backend.classes.documents_class import DocumentsClass

    result = DocumentsClass.fill_docx_form(
        str(template_path),
        replacements,
        str(out_path),
    )
    if result.get("status") == "error":
        raise RuntimeError(result.get("message") or "fill_docx_form falló")


def create_familia_base_for_gpt(
    agent_id: str,
    student_context: dict[str, Any],
    template_path: Path,
) -> dict[str, Any]:
    """Genera .docx base con identificación desde BD (sin fila en BD de respuestas)."""
    ensure_responses_dir(agent_id)
    student_name = student_context.get("student_full_name") or "Estudiante"
    display_name = f"Informe_familia_{_safe_filename(str(student_name))}.docx"
    token = uuid.uuid4().hex[:10]
    disk_path = agent_dir(agent_id) / "responses" / f"_base_{token}_{display_name}"
    disk_path.parent.mkdir(parents=True, exist_ok=True)

    replacements = build_familia_identification_replacements(student_context)
    _fill_and_save(template_path, disk_path, replacements)

    return {
        "disk_path": disk_path,
        "display_name": display_name,
        "template_name": template_path.name,
    }


def generate_familia_report_docx(
    db: Session,
    agent_id: str,
    student_context: dict[str, Any],
    template_path: Path,
) -> dict[str, Any]:
    """Informe completo solo desde BD (fallback sin OpenAI)."""
    ensure_responses_dir(agent_id)
    student_name = student_context.get("student_full_name") or "Estudiante"
    visible_name = f"Informe_familia_{_safe_filename(str(student_name))}.docx"
    storage_path, visible = build_response_storage_path(visible_name)
    out_path = agent_dir(agent_id) / storage_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    replacements = build_familia_form_replacements(student_context)
    _fill_and_save(template_path, out_path, replacements)

    now = datetime.utcnow()
    row = AgentResponseFileModel(
        id=storage_path,
        agent_id=agent_id,
        display_name=visible,
        size_bytes=out_path.stat().st_size,
        openai_container_id="pie360-form",
        openai_file_id="pie360-form",
        created_at=now,
    )
    db.add(row)
    db.flush()

    return {
        "id": row.id,
        "name": row.display_name,
        "size": int(row.size_bytes or 0),
        "createdAt": row.created_at.isoformat() if row.created_at else None,
    }


def can_use_familia_hybrid(
    message: str,
    student_context: dict[str, Any] | None,
    selected_rows: list[Any],
    agent_id: str,
) -> Path | None:
    if _message_intent(message) != "familia":
        return None
    if not student_context or not student_context.get("student_id"):
        return None
    return resolve_form_template_for_generation(agent_id, selected_rows)


def try_deterministic_familia_report(
    db: Session,
    agent_id: str,
    message: str,
    selected_rows: list[Any],
    student_context: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Solo cuando no hay OpenAI: informe completo desde BD."""
    template_path = can_use_familia_hybrid(message, student_context, selected_rows, agent_id)
    if not template_path or not student_context:
        return None

    file_dict = generate_familia_report_docx(db, agent_id, student_context, template_path)
    student_name = student_context.get("student_full_name") or "el estudiante"
    return {
        "reply": (
            f"Generé el Informe para la Familia de {student_name} desde PIE360 "
            f"(plantilla «{template_path.name}»). Descarga el archivo adjunto."
        ),
        "responseFiles": [file_dict],
        "openaiFilesUsed": 0,
        "containerId": None,
        "model": "pie360-fill_docx_form",
        "templateUsed": template_path.name,
    }
