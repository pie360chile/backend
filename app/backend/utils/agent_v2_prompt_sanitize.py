"""Ajusta el prompt del agente para el chat: omite secciones que el sistema reemplaza."""

from __future__ import annotations

import re

# Secciones del prompt que no aplican: la salida la maneja PIE360 (plantilla + BD).
_OMIT_SECTION_KEYWORDS = (
    "salida esperada",
    "guardado de informes",
    "confirmación de guardado",
    "confirmacion de guardado",
)

_SECTION_HEADER = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def _should_omit_section(title: str) -> bool:
    normalized = title.strip().lower()
    return any(keyword in normalized for keyword in _OMIT_SECTION_KEYWORDS)


def sanitize_role_instructions_for_chat(text: str) -> str:
    """Elimina secciones como «Salida esperada» antes de enviar el prompt al modelo."""
    raw = (text or "").strip()
    if not raw:
        return raw

    matches = list(_SECTION_HEADER.finditer(raw))
    if not matches:
        return raw

    parts: list[str] = []
    prefix = raw[: matches[0].start()].strip()
    if prefix:
        parts.append(prefix)

    for index, match in enumerate(matches):
        title = match.group(1)
        if _should_omit_section(title):
            continue
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        parts.append(raw[start:end].strip())

    return "\n\n".join(parts).strip()


CHAT_OUTPUT_OVERRIDE = """
## Salida real en PIE360 Agent v2 (prioridad máxima — reemplaza «Salida esperada»)

Ignora instrucciones sobre:
- presentar informes largos en el chat como entrega final;
- generar archivos .docx/.pdf descargables manualmente;
- crear ZIP o paquetes comprimidos;
- subir a Google Drive o usar herramientas MCP de guardado;
- confirmaciones de guardado con rutas de Drive.

La salida del sistema SIEMPRE es:
1. Usar los archivos de Files y el mensaje del usuario como fuente.
2. Producir el contenido para rellenar la plantilla del documento PIE360 activo.
3. El backend completa la plantilla Word o PDF y guarda el archivo en la base de datos del estudiante (tabla folders).

En el chat responde de forma breve: resumen de lo analizado, datos usados o faltantes.
No entregues el informe completo en texto si corresponde generar documento.
""".strip()
