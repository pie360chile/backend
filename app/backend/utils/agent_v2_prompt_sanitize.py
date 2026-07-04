"""Ajusta el prompt del agente para el chat: omite secciones que el sistema reemplaza."""

from __future__ import annotations

import re

# Solo se omiten secciones de ENTREGA (Word/Drive); no las de fuentes ni archivos.
_OMIT_SECTION_KEYWORDS = (
    "salida esperada",
    "guardado de informes",
    "confirmación de guardado",
    "confirmacion de guardado",
)

# Líneas del prompt del usuario que deben repetirse con prioridad (fuentes/archivos).
_PRIORITY_LINE_MARKERS = (
    "reporte_interactivo",
    "reporte interactivo",
    ".xls",
    ".xlsx",
    "excel",
    "files",
    "archivo",
    "archivos",
    "fuente",
    "fuentes",
    "apoderado",
    "nomina",
    "nómina",
    "profesional",
    "normativa",
    "decreto",
    "glosario",
    "antecedentes",
    "informe psicoped",
    "prioriz",
    "obligatori",
    "debes ",
    "debe ",
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


def extract_priority_directives_from_prompt(text: str) -> str:
    """
    Extrae del prompt del creador las reglas operativas (archivos, fuentes, apoderado, etc.)
    para reforzarlas después del contexto de Files.
    """
    raw = (text or "").strip()
    if not raw:
        return ""

    seen: set[str] = set()
    bullets: list[str] = []

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        low = stripped.lower()
        if not any(marker in low for marker in _PRIORITY_LINE_MARKERS):
            continue
        cleaned = re.sub(r"^[-*•]\s+", "", stripped)
        if len(cleaned) < 12:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        bullets.append(cleaned)

    if not bullets:
        return ""

    return (
        "## Directrices del creador del agente (OBLIGATORIAS — prevalecen sobre brevedad del chat)\n"
        + "\n".join(f"- {b}" for b in bullets[:40])
    )


CHAT_OUTPUT_OVERRIDE = """
## Formato de entrega en PIE360 (solo esto reemplaza «Salida esperada»)

Estas reglas aplican únicamente a CÓMO se entrega el resultado, no a qué archivos consultar
ni a cómo redactar según las instrucciones del agente.

Ignora instrucciones del prompt sobre:
- presentar informes largos en el chat como entrega final;
- generar archivos .docx/.pdf descargables manualmente;
- crear ZIP o paquetes comprimidos;
- subir a Google Drive o usar herramientas MCP de guardado;
- confirmaciones de guardado con rutas de Drive.

La entrega técnica SIEMPRE es:
1. Consultar las fuentes indicadas en las instrucciones del agente y en ARCHIVOS DE CONTEXTO.
2. Producir el contenido para rellenar la plantilla del documento PIE360 activo.
3. El backend completa la plantilla Word o PDF y guarda el archivo en la base de datos del estudiante.

En el chat: resumen breve de lo analizado, archivos usados y datos faltantes.
No pegues el informe completo en el chat si corresponde generar documento Word.

Identificación del estudiante:
- Si aún no hay estudiante identificado, pide el RUT o IPE antes de afirmar que el Word fue generado.

Descarga:
- Cuando el backend genere el archivo, el chat mostrará el botón «Descargar archivo generado».
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
- Obedece las directrices del creador del agente sobre qué archivo usar (p. ej. REPORTE_INTERACTIVO*.xls).
- Búscalos en ARCHIVOS DE CONTEXTO, DATOS EXTRAÍDOS DE EXCEL y datos de ficha PIE360 del estudiante.
- Si el prompt del agente indica un archivo concreto, priorízalo para apoderado y contacto.
- Si tras revisar esas fuentes no hay dato verificable, deja el campo vacío (no inventes).

Formato:
- Español formal de informes psicopedagógicos ministeriales chilenos.
- Fechas en dd/mm/aaaa cuando corresponda.
- Si no hay datos verificables para un campo, usa cadena vacía.
""".strip()
