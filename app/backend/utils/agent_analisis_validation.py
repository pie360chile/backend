"""Validación de fidelidad del JSON de análisis vs contenido del Word."""

from __future__ import annotations

import re
from typing import Any

# Longitud mínima aproximada del texto íntegro por sección (informe familia).
_FAMILIA_MIN_CHARS: dict[str, int] = {
    "resultados_evaluacion": 80,
    "ambito_pedagogico": 200,
    "ambito_social_afectivo": 200,
    "trabajo_colaborativo": 120,
    "apoyos_hogar": 120,
}

_FAMILIA_ACUERDOS_MIN = 150

_VAGUE_ACUERDOS = re.compile(
    r"tres compromisos|compromiso compartido escuela|escuela, familia y",
    re.IGNORECASE,
)

_TRUNCATION_MARKERS = ("...", "…")


def _is_truncated(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if any(marker in stripped for marker in _TRUNCATION_MARKERS):
        return True
    if stripped.endswith(">"):
        return True
    return False


def _check_string_section(key: str, value: str, min_chars: int | None) -> None:
    if _is_truncated(value):
        raise ValueError(
            f"secciones.{key} parece truncado o resumido. "
            "Debe contener el texto íntegro que va en el Word, sin '...' ni extractos."
        )
    if min_chars is not None and len(value.strip()) < min_chars:
        raise ValueError(
            f"secciones.{key} es demasiado corto ({len(value.strip())} caracteres; "
            f"mínimo ~{min_chars}). Copia el párrafo completo del informe, no un resumen."
        )


def validate_analisis_payload(payload: dict[str, Any]) -> None:
    """Exige que secciones reflejen el texto completo del Word, no resúmenes."""
    secciones = payload.get("secciones")
    if not isinstance(secciones, dict) or not secciones:
        raise ValueError(
            "secciones debe ser un objeto con el texto completo de cada apartado del informe."
        )

    tipo = (payload.get("tipo_informe") or "").strip().lower()

    for key, value in secciones.items():
        if isinstance(value, str):
            min_chars = _FAMILIA_MIN_CHARS.get(key) if tipo == "familia" else None
            _check_string_section(key, value, min_chars)

            if key == "acuerdos" and tipo == "familia":
                if _VAGUE_ACUERDOS.search(value) and len(value.strip()) < _FAMILIA_ACUERDOS_MIN:
                    raise ValueError(
                        "secciones.acuerdos debe incluir los 3 compromisos redactados por completo "
                        "(escuela, familia y compartido), no una frase genérica."
                    )
        elif isinstance(value, list):
            if not value:
                raise ValueError(f"secciones.{key} no puede estar vacío.")
            for i, item in enumerate(value):
                if not isinstance(item, str):
                    continue
                if _is_truncated(item):
                    raise ValueError(
                        f"secciones.{key}[{i}] parece truncado. "
                        "Cada ítem debe ser el texto completo del Word."
                    )
