"""Normaliza fields del LLM → tags de la plantilla Word doc 27 (agente)."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Any

PSYCHOPED_DOCUMENT_ID = 27

# Tag del control (normalizado) → clave canónica en replacements (tags del DOCX)
PSYCHOPED_CONTENT_CONTROL_ALIASES: dict[str, str] = {
    # Identificación (español / form web → plantilla)
    "nombre_identidad_estudiante": "student_full_name",
    "nombre_de_identidad_estudiante": "student_full_name",
    "nombre_identidad_del_estudiante": "student_full_name",
    "nombre_completo_estudiante": "student_full_name",
    "nombre_y_apellidos_del_estudiante": "student_full_name",
    "social_name": "student_social_name",
    "nombre_social_del_estudiante": "student_social_name",
    "nombre_social_estudiante": "student_social_name",
    "nombre_social": "student_social_name",
    "fecha_de_nacimiento": "birth_day",
    "fecha_nacimiento": "birth_day",
    "age": "student_age",
    "edad": "student_age",
    "edad_del_estudiante": "student_age",
    "establecimiento_educacional": "student_school",
    "establecimiento": "student_school",
    "nombre_establecimiento": "student_school",
    "colegio": "student_school",
    "curso_nivel": "student_course",
    "curso_o_nivel": "student_course",
    "curso": "student_course",
    "nivel": "student_course",
    "fecha_de_evaluacion": "evaluation_date",
    "fecha_evaluacion": "evaluation_date",
    # Diagnóstico (formulario usa diagnosis; plantilla usa diagnostic)
    "diagnostico": "diagnostic",
    "diagnosis": "diagnostic",
    "diagnosis_issue_date": "issue_date",
    "fecha_de_emision_de_diagnostico": "issue_date",
    "fecha_emision_diagnostico": "issue_date",
    "fecha_emision_del_diagnostico": "issue_date",
    "fecha_emision_de_diagnostico": "issue_date",
    # Narrativos
    "analisis_cognitivo": "cognitive_analysis",
    "analisis_cognitivo_comunicativo": "cognitive_analysis",
    "analisis_personal_socioemocional": "personal_analysis",
    "analisis_motor_autonomia_sensorial": "motor_analysis",
    "sintesis_cognitiva": "cognitive_synthesis",
    "sintesis_personal": "personal_synthesis",
    "sintesis_motora": "motor_synthesis",
    "sugerencias_al_establecimiento": "suggestions_to_school",
    "sugerencias_al_equipo_de_aula": "suggestions_to_classroom_team",
    "sugerencias_al_estudiante": "suggestions_to_student",
    "sugerencias_a_la_familia": "suggestions_to_family",
    "otras_sugerencias": "other_suggestions",
    "conclusion_informe": "conclusion",
    "instrumentos_aplicados": "instruments_applied",
    "antecedentes_historia_escolar": "school_history_background",
    "nombre_profesional": "professional_full_name",
    "rut_profesional": "professional_identification_number",
    "registro_profesional": "professional_registration_number",
    "especialidad_profesional": "professional_specialty",
}

_SUGGESTION_KEYS = {
    "suggestions_to_school",
    "suggestions_to_classroom_team",
    "suggestions_to_student",
    "suggestions_to_family",
    "other_suggestions",
    "sugerencias_al_establecimiento",
    "sugerencias_al_equipo_de_aula",
    "sugerencias_al_estudiante",
    "sugerencias_a_la_familia",
    "otras_sugerencias",
}


def format_suggestions_as_dashes(text: str) -> str:
    """Convierte recomendaciones a lista con '- ' (un ítem por línea)."""
    raw = (text or "").strip()
    if not raw:
        return raw
    chunk = re.sub(r"\r\n?", "\n", raw)
    chunk = re.sub(r"(?m)^\s*(?:\d+\s*[.)\-]+|[-•*–—])\s*", "\n", chunk)
    chunk = re.sub(r"(?:\n\s*)?(?<!\d)(\d+)\s*[.)\-]+\s+", "\n", chunk)
    parts = [re.sub(r"\s+", " ", p).strip(" \t-•*–—") for p in chunk.split("\n")]
    items = [p for p in parts if p]
    if len(items) <= 1 and re.search(r"[.!?]\s+\S", raw):
        items = [
            re.sub(r"\s+", " ", s).strip(" \t-•*–—")
            for s in re.split(r"(?<=[.!?])\s+", raw)
            if s.strip()
        ]
        items = [p for p in items if p]
    if not items:
        return raw
    return "\n".join(f"- {item.rstrip('.')}" for item in items)


# Claves del formulario/LLM → tags de plantilla (copia de valor)
_FORM_TO_TEMPLATE: dict[str, str] = {
    "diagnosis": "diagnostic",
    "diagnosis_issue_date": "issue_date",
    "social_name": "student_social_name",
    "age": "student_age",
}


_DATE_KEY_HINTS = (
    "date",
    "fecha",
    "birth_day",
    "born",
)
_MONTHS_ES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def _is_date_field_key(key: str) -> bool:
    k = _normalize_key(key)
    return any(h in k for h in _DATE_KEY_HINTS)


def format_psychoped_date(value: str) -> str:
    """Normaliza fechas del informe psicopedagógico a dd-mm-YYYY."""
    raw = (value or "").strip()
    if not raw:
        return raw
    if re.fullmatch(r"\d{2}-\d{2}-\d{4}", raw):
        return raw

    parsed: date | None = None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            parsed = datetime.strptime(raw[:10], fmt).date()
            break
        except ValueError:
            continue
    if parsed is None:
        m = re.search(
            r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s*(?:de|,)?\s*(\d{4})",
            raw.lower(),
        )
        if m:
            month = _MONTHS_ES.get(m.group(2))
            if month:
                try:
                    parsed = date(int(m.group(3)), month, int(m.group(1)))
                except ValueError:
                    parsed = None
    if parsed is None:
        m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", raw)
        if m:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            # Si el primer número > 12, es día-mes.
            if d > 12:
                try:
                    parsed = date(y, mo, d)
                except ValueError:
                    parsed = None
            elif mo > 12:
                try:
                    parsed = date(y, d, mo)
                except ValueError:
                    parsed = None
            else:
                try:
                    parsed = date(y, mo, d)
                except ValueError:
                    parsed = None
    if parsed is None:
        return raw
    return parsed.strftime("%d-%m-%Y")


def _normalize_key(key: str) -> str:
    t = (key or "").strip().lower()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9]+", "_", t)
    return re.sub(r"_+", "_", t).strip("_")


def _scale_value_to_col(v: str) -> int | None:
    u = (v or "").strip().upper()
    if u in ("1",):
        return 1
    if u in ("2",):
        return 2
    if u in ("3",):
        return 3
    if u in ("N/O", "NO", "N-O", "N_O"):
        return 4
    return None


def _apply_admission_type(merged: dict[str, str], raw: str) -> None:
    """admission_type del form → admission_type_1|2|3 en plantilla."""
    if any(merged.get(f"admission_type_{i}") for i in (1, 2, 3)):
        return
    val = (raw or "").strip().lower()
    other = (merged.get("admission_type_other") or "").strip()
    if val in ("ingreso", "ingreso_pie", "nuevo"):
        merged["admission_type_1"] = "X"
    elif val in ("reevaluacion", "reevaluación", "re_evaluacion"):
        merged["admission_type_2"] = "X"
    elif val in ("otro", "otra", "otros"):
        merged["admission_type_3"] = other or "X"
    elif val:
        # Texto libre: marcar OTRO
        merged["admission_type_3"] = raw.strip() if raw.strip() else "X"


def _apply_form_scales(merged: dict[str, str], source: dict[str, str]) -> None:
    """pedagogical_scale_N / social_communicative_scale_N → scale_row_col."""
    if any(k.startswith("scale_") for k in merged):
        return
    for n in range(1, 11):
        ped = source.get(f"pedagogical_scale_{n}") or merged.get(f"pedagogical_scale_{n}")
        if ped:
            col = _scale_value_to_col(str(ped))
            if col:
                for c in range(1, 5):
                    merged[f"scale_{n}_{c}"] = "X" if c == col else ""
        soc = source.get(f"social_communicative_scale_{n}") or merged.get(
            f"social_communicative_scale_{n}"
        )
        if soc:
            col = _scale_value_to_col(str(soc))
            if col:
                row = n + 10
                for c in range(1, 5):
                    merged[f"scale_{row}_{c}"] = "X" if c == col else ""


def normalize_psychoped_replacements(
    llm_fields: dict[str, Any],
    student_ctx: dict[str, Any] | None = None,
) -> dict[str, str]:
    """
    Une campos del LLM con aliases hacia tags de la plantilla doc 27.
    No borra claves originales (por si la plantilla usa nombres del form).
    """
    merged: dict[str, str] = {}
    raw: dict[str, str] = {}

    for key, value in (llm_fields or {}).items():
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        k = str(key).strip()
        if not k:
            continue
        if _is_date_field_key(k):
            text = format_psychoped_date(text)
        raw[k] = text
        merged[k] = text
        nk = _normalize_key(k)
        canon = PSYCHOPED_CONTENT_CONTROL_ALIASES.get(nk)
        if canon and canon not in merged:
            merged[canon] = text
        form_map = _FORM_TO_TEMPLATE.get(nk) or _FORM_TO_TEMPLATE.get(k)
        if form_map and form_map not in merged:
            merged[form_map] = text

    admission = raw.get("admission_type") or merged.get("admission_type") or ""
    if admission:
        _apply_admission_type(merged, admission)

    _apply_form_scales(merged, raw)

    ctx = student_ctx or {}
    full_name = (ctx.get("student_fullname") or "").strip()
    if full_name:
        merged.setdefault("student_full_name", full_name)

    for key, text in list(merged.items()):
        if _is_date_field_key(key):
            merged[key] = format_psychoped_date(str(text))
        elif _normalize_key(key) in {_normalize_key(k) for k in _SUGGESTION_KEYS} or key in _SUGGESTION_KEYS:
            merged[key] = format_suggestions_as_dashes(str(text))

    return merged
