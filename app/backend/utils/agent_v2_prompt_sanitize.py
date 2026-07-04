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

Identificación del estudiante:
- Si aún no hay estudiante identificado en el sistema para esta conversación, pide el RUT o IPE para ubicarlo en PIE360 antes de afirmar que el Word fue generado.
- No digas «informe generado» ni «listo para descargar» si faltan RUT/IPE y el usuario no ha sido identificado en la plataforma.

Descarga:
- Cuando el backend genere el archivo, el chat mostrará el botón «Descargar archivo generado» debajo de tu mensaje.
""".strip()


DOCUMENT_FIELD_EXTRACTION_GUIDE = """
## Relleno del documento Word/PDF (extractor — prioridad máxima)

Genera el texto COMPLETO que se imprimirá en cada campo de la plantilla.
NO resumas. NO uses frases telegráficas. NO te quedes con el resumen breve del chat.

Fuentes (en este orden):
1. Archivos de contexto (Files) — fuente principal y obligatoria cuando existan
2. Mensaje del usuario
3. Respuesta del asistente — solo orientación; si es breve, expande con los archivos

Campos narrativos (p. ej. diagnostic, applied_instruments, pedagogical_field_1,
pedagogical_field_2, social_field_1, social_field_2, collaborative_work, supports,
agreements y campos equivalentes de otros informes):
- Redacta párrafos completos, claros y profesionales según las Normas de redacción del agente.
- Desarrolla fortalezas, necesidades, antecedentes, apoyos y acuerdos con detalle basado en evidencia.
- Cuando haya información en los archivos, escribe al menos 3–8 oraciones por campo narrativo.
- No dejes un campo narrativo en una sola frase corta si los antecedentes lo permiten.

Campos de identificación (nombre, RUT/IPE, curso, establecimiento, edad, fecha de nacimiento, etc.):
- Solo el dato puntual, sin párrafos extensos.

Checkboxes (apoderado titular/suplente, poder simple sí/no, evaluación ingreso/reevaluación):
- Marca solo si hay dato explícito en archivos o mensaje (guardian_type, has_power_of_attorney, evaluation_type).
- Si no hay información verificable, deja el checkbox SIN marcar (cadena vacía o false; no uses «x», «1» ni «sí» por defecto).

Datos del apoderado / receptor y del profesional que entrega el informe:
- Búscalos en TODOS los archivos del índice de Files (incluidos Excel .xls/.xlsx como reportes interactivos).
- Si el prompt del agente indica un archivo concreto (p. ej. REPORTE_INTERACTIVO*.xls), priorízalo para apoderado y contacto.
- Si tras revisar los archivos incluidos en contexto no hay dato verificable, deja el campo vacío (no inventes).

Formato:
- Español formal de informes psicopedagógicos ministeriales chilenos.
- Fechas en dd/mm/aaaa cuando corresponda.
- Si no hay datos verificables para un campo, usa cadena vacía.
""".strip()
