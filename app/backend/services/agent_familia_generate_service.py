"""Generación determinística del informe familia (plantilla formulario + BD PIE360)."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.db.models import AgentResponseFileModel
from app.backend.utils.agent_familia_prefill import build_familia_form_replacements
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


def generate_familia_report_docx(
    db: Session,
    agent_id: str,
    student_context: dict[str, Any],
    template_path: Path,
) -> dict[str, Any]:
    """Rellena plantilla formulario con fill_docx_form y persiste en responses/."""
    from app.backend.classes.documents_class import DocumentsClass

    ensure_responses_dir(agent_id)
    student_name = student_context.get("student_full_name") or "Estudiante"
    visible_name = f"Informe_familia_{_safe_filename(str(student_name))}.docx"
    storage_path, visible = build_response_storage_path(visible_name)
    out_path = agent_dir(agent_id) / storage_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    replacements = build_familia_form_replacements(student_context)
    eval_type = str(student_context.get("evaluation_type") or "").strip().lower()
    if eval_type in ("admission", "admisión", "ingreso", "1"):
        replacements["evaluation"] = "1"
        replacements["Evaluación de Ingreso"] = "x"
    elif eval_type in ("revaluation", "reevaluación", "2"):
        replacements["reevaluation"] = "1"

    result = DocumentsClass.fill_docx_form(
        str(template_path),
        replacements,
        str(out_path),
    )
    if result.get("status") == "error":
        raise RuntimeError(result.get("message") or "fill_docx_form falló")

    content = out_path.read_bytes()
    now = datetime.utcnow()
    row = AgentResponseFileModel(
        id=storage_path,
        agent_id=agent_id,
        display_name=visible,
        size_bytes=len(content),
        openai_container_id="pie360-form",
        openai_file_id="pie360-form",
        created_at=now,
    )
    db.add(row)
    db.flush()

    file_dict = {
        "id": row.id,
        "name": row.display_name,
        "size": int(row.size_bytes or 0),
        "createdAt": row.created_at.isoformat() if row.created_at else None,
    }
    logger.info(
        "Informe familia generado (determinístico) agente=%s estudiante=%s plantilla=%s",
        agent_id,
        student_context.get("student_id"),
        template_path.name,
    )
    return file_dict


def try_deterministic_familia_report(
    db: Session,
    agent_id: str,
    message: str,
    selected_rows: list[Any],
    student_context: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """
    Si hay estudiante en BD y plantilla formulario, genera el .docx sin code interpreter.
    Devuelve payload tipo chat done o None para continuar con OpenAI.
    """
    if _message_intent(message) != "familia":
        return None
    if not student_context or not student_context.get("student_id"):
        return None

    template_path = resolve_form_template_for_generation(agent_id, selected_rows)
    if not template_path:
        return None

    file_dict = generate_familia_report_docx(db, agent_id, student_context, template_path)
    student_name = student_context.get("student_full_name") or "el estudiante"
    reply = (
        f"Generé el Informe para la Familia de {student_name} usando la plantilla "
        f"formulario «{template_path.name}» y los datos de PIE360 (estudiante, "
        f"profesional y apoderado cuando existen en la base de datos). "
        f"Descarga el archivo adjunto. "
        f"Si necesitas ampliar textos narrativos desde la cartilla o evaluación del caso, "
        f"pídelo en un mensaje aparte."
    )
    return {
        "reply": reply,
        "responseFiles": [file_dict],
        "openaiFilesUsed": 0,
        "containerId": None,
        "model": "pie360-fill_docx_form",
        "deterministic": True,
        "templateUsed": template_path.name,
    }
