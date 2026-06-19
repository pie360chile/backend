"""Relleno de identificación en informe familia vía placeholders {{clave}} sin romper la plantilla."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Claves que van en tablas 1 y 2 (identificación). Narrativa sigue en tabla 3.
FAMILIA_IDENTIFICATION_KEYS: frozenset[str] = frozenset(
    {
        "student_full_name",
        "student_social_name",
        "student_identification_number",
        "student_birth_date",
        "student_born_date",
        "student_age",
        "student_course",
        "student_school",
        "professional_full_name",
        "professional_social_name",
        "professional_identification_number",
        "professional_job_position",
        "professional_phone",
        "professional_email",
        "professional_phone_email",
        "professional_delivered_date_inform",
        "person_full_name",
        "receiver_social_name",
        "person_identification_number",
        "person_relation_student",
        "person_presence",
        "person_phone",
        "person_email",
    }
)

_PLACEHOLDER_RE = re.compile(
    r"\{\{([a-zA-Z0-9_]+)\}\}|\{([a-zA-Z0-9_]+)\}|\[([a-zA-Z0-9_]+)\]"
)


def _formats_for_tag(tag: str) -> tuple[str, ...]:
    return (f"{{{{{tag}}}}}", f"{{{tag}}}", f"[{tag}]")


def docx_has_familia_placeholders(path: Path) -> bool:
    """True si el .docx contiene al menos un placeholder de identificación."""
    try:
        from docx import Document
        from docx.oxml.ns import qn

        doc = Document(str(path))
        for t in doc.element.body.iter(qn("w:t")):
            text = t.text or ""
            if not text:
                continue
            for m in _PLACEHOLDER_RE.finditer(text):
                key = m.group(1) or m.group(2) or m.group(3)
                if key in FAMILIA_IDENTIFICATION_KEYS:
                    return True
        return False
    except Exception:
        return False


def _replace_text_placeholders(text: str, replacements: dict[str, str]) -> str:
    result = text
    for tag, value in replacements.items():
        val = str(value) if value is not None else ""
        for fmt in _formats_for_tag(tag):
            result = result.replace(fmt, val)
    return result


def _walk_all_wt_elements(doc: Any, qn: Any):
    for t in doc.element.body.iter(qn("w:t")):
        yield t
    for section in doc.sections:
        for hf in (
            section.header,
            section.footer,
            section.first_page_header,
            section.first_page_footer,
        ):
            if hf is None or hf._element is None:
                continue
            for t in hf._element.iter(qn("w:t")):
                yield t


def replace_familia_placeholders_in_doc(
    doc: Any,
    replacements: dict[str, str],
    *,
    keys_filter: frozenset[str] | None = None,
) -> list[str]:
    """
    Sustituye {{clave}} / {clave} / [clave] dentro de w:t sin borrar párrafos ni celdas.
    Preserva etiquetas, cuadros ☐ y formato de la plantilla.
    """
    from docx.oxml.ns import qn

    filtered = replacements
    if keys_filter is not None:
        filtered = {k: v for k, v in replacements.items() if k in keys_filter}

    if not filtered:
        return []

    filled: list[str] = []
    for wt in _walk_all_wt_elements(doc, qn):
        original = wt.text or ""
        if not original:
            continue
        if not any(fmt in original for tag in filtered for fmt in _formats_for_tag(tag)):
            continue
        new_text = _replace_text_placeholders(original, filtered)
        if new_text != original:
            wt.text = new_text
            for tag in filtered:
                if any(fmt in original for fmt in _formats_for_tag(tag)):
                    filled.append(tag)
                    break

    return sorted(set(filled))


def fill_familia_identification_placeholders(
    template_path: str | Path,
    replacements: dict[str, str],
    output_path: str | Path,
) -> dict[str, Any]:
    """Copia plantilla y reemplaza solo placeholders de identificación."""
    import shutil

    from docx import Document

    template_path = Path(template_path)
    output_path = Path(output_path)
    if template_path.resolve() != output_path.resolve():
        shutil.copy2(template_path, output_path)

    doc = Document(str(output_path))
    id_replacements = {k: v for k, v in replacements.items() if k in FAMILIA_IDENTIFICATION_KEYS}
    filled = replace_familia_placeholders_in_doc(
        doc, id_replacements, keys_filter=FAMILIA_IDENTIFICATION_KEYS
    )
    doc.save(str(output_path))
    logger.info(
        "Placeholders identificación: %d claves en %s",
        len(filled),
        output_path.name,
    )
    return {"status": "success", "filled_keys": filled, "mode": "placeholders"}


def restore_identification_from_context(docx_path: Path, student_context: dict[str, Any]) -> None:
    """Reaplica identificación desde BD sobre un .docx ya generado (corrige si GPT tocó tablas 1-2)."""
    from docx import Document

    from app.backend.utils.agent_familia_prefill import build_familia_identification_replacements

    if not docx_has_familia_placeholders(docx_path):
        return
    replacements = build_familia_identification_replacements(student_context)
    doc = Document(str(docx_path))
    replace_familia_placeholders_in_doc(
        doc, replacements, keys_filter=FAMILIA_IDENTIFICATION_KEYS
    )
    doc.save(str(docx_path))
