"""Detección y reglas de plantilla para informe a la familia del agente."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    asciiish = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", asciiish.lower()).strip()


def is_familia_form_template(display_name: str) -> bool:
    """Plantilla PIE360 con campos de formulario (content controls)."""
    lower = _normalize(display_name.replace("_", " ").replace("-", " "))
    if not lower:
        return False
    if "family report" in lower or "family_report" in lower.replace(" ", "_"):
        return True
    if "family_report" in lower:
        return True
    if "formulario" in lower and "familia" in lower:
        return True
    if "informe familiar" in lower or "informe_familiar" in lower.replace(" ", "_"):
        return True
    if "con formulario" in lower or "tipo formulario" in lower:
        return True
    # Generado desde admin o plantilla PIE360 (no el formato ministerial vacío)
    if "informe familia" in lower or "informe_familia" in lower.replace(" ", "_"):
        if "formato" not in lower:
            return True
    return False


def agent_has_familia_form_template(
    file_names: list[str],
    *,
    file_paths: dict[str, Path] | None = None,
) -> bool:
    for name in file_names or []:
        if is_familia_form_file(name, (file_paths or {}).get(name)):
            return True
    return False


def filter_familia_template_file_names(
    file_names: list[str],
    *,
    file_paths: dict[str, Path] | None = None,
) -> list[str]:
    """Si hay plantilla formulario, excluye FORMATO INFORME DE FAMILIA (tablas)."""
    names = file_names or []
    if not agent_has_familia_form_template(names, file_paths=file_paths):
        return names
    return [
        n
        for n in names
        if not is_familia_tabla_file(n, (file_paths or {}).get(n))
    ]


def build_form_template_supremacy_block(base_filename: str, excluded: list[str]) -> str:
    excluded_txt = ", ".join(f"«{n}»" for n in excluded) if excluded else "(ninguno)"
    return (
        "=== PLANTILLA FORMULARIO — PRIORIDAD SOBRE FORMATO MINISTERIAL ===\n"
        f"OBLIGATORIO: genera el informe copiando y rellenando SOLO «{base_filename}».\n"
        f"PROHIBIDO abrir o completar plantillas de tablas ministeriales: {excluded_txt}.\n"
        "Pasos: (1) lee bloque DATOS EN BASE DE DATOS; (2) shutil.copy plantilla formulario; "
        "(3) rellena content controls / placeholders; (4) completa narrativa desde archivos del caso.\n"
    )


def docx_has_form_controls(path: Path) -> bool:
    """True si el .docx tiene content controls (plantilla formulario PIE360)."""
    try:
        from docx import Document
        from docx.oxml.ns import qn

        doc = Document(str(path))
        count = sum(1 for _ in doc.element.body.iter(qn("w:sdt")))
        return count >= 3
    except Exception:
        return False


def is_familia_form_file(display_name: str, disk_path: Path | None = None) -> bool:
    if is_familia_form_template(display_name):
        return True
    if disk_path and disk_path.suffix.lower() == ".docx" and disk_path.is_file():
        return docx_has_form_controls(disk_path)
    return False


def is_familia_tabla_file(display_name: str, disk_path: Path | None = None) -> bool:
    if is_familia_form_file(display_name, disk_path):
        return False
    return is_familia_tabla_template(display_name)


def is_familia_tabla_template(display_name: str) -> bool:
    """FORMATO INFORME DE FAMILIA.docx (tablas etiqueta/valor)."""
    lower = _normalize(display_name.replace("_", " ").replace("-", " "))
    return ("formato" in lower and "familia" in lower) or "informe de familia" in lower


def familia_form_template_priority(display_name: str) -> int:
    lower = _normalize(display_name.replace("_", " ").replace("-", " "))
    if "family_report" in lower:
        return 0
    if is_familia_form_template(display_name):
        return 1
    if "cartilla" in lower:
        return 2
    if is_familia_tabla_template(display_name):
        return 10
    return 20


def pick_familia_base_template(
    file_names: list[str] | None,
    *,
    agent_id: str | None = None,
    file_paths: dict[str, Path] | None = None,
) -> tuple[str | None, str]:
    """Devuelve (nombre_archivo, tipo) con tipo form | tabla | none."""
    names = file_names or []
    form: list[str] = []
    tabla: list[str] = []
    for name in names:
        disk = (file_paths or {}).get(name)
        if is_familia_form_file(name, disk):
            form.append(name)
        elif is_familia_tabla_file(name, disk):
            tabla.append(name)
    if form:
        form.sort(key=familia_form_template_priority)
        return form[0], "form"
    if tabla:
        return tabla[0], "tabla"
    return None, "none"


def resolve_familia_template_from_rows(
    agent_id: str,
    rows: list[Any],
) -> tuple[str | None, str]:
    """Clasifica plantilla familia inspeccionando archivos en disco."""
    from app.backend.utils.agent_files import agent_dir

    names: list[str] = []
    paths: dict[str, Path] = {}
    for row in rows:
        name = getattr(row, "display_name", None) or ""
        if not name:
            continue
        names.append(name)
        fid = getattr(row, "id", None)
        if fid:
            paths[name] = agent_dir(agent_id) / fid
    return pick_familia_base_template(names, file_paths=paths)


def resolve_form_template_path(agent_id: str, rows: list[Any]) -> Path | None:
    """Ruta en disco de la plantilla formulario familia, si existe."""
    from app.backend.utils.agent_files import agent_dir

    base, kind = resolve_familia_template_from_rows(agent_id, rows)
    if kind != "form" or not base:
        return None
    for row in rows:
        name = getattr(row, "display_name", None) or ""
        fid = getattr(row, "id", None)
        if name == base and fid:
            path = agent_dir(agent_id) / fid
            if path.is_file():
                return path
    return None


def build_no_fabrication_rules() -> str:
    """Prohibición de inventar datos no presentes en BD o archivos."""
    return (
        "- NO INVENTAR DATOS (OBLIGATORIO): usa únicamente información que esté en "
        "«DATOS DEL ESTUDIANTE EN BASE DE DATOS», en los archivos del caso o en el rol. "
        "Prohibido fabricar fechas, calendarizaciones, nombres, RUT, diagnósticos o frases "
        "genéricas del tipo «Según calendarización del establecimiento», "
        "«antecedente no informado» como párrafo, o textos explicativos en celdas de fecha.\n"
        "- Si falta un dato: en campos de identificación escribe «No informado»; "
        "en celdas de FECHA deja la celda vacía (no escribas nada). "
        "Nunca sustituyas una fecha faltante por un párrafo.\n"
        "- Fechas de seguimiento → doc.tables[3] fila 17: solo fechas DD/MM/YYYY "
        "en las celdas de valor (cols 4-9), una por celda asignada. "
        "Usa evaluation_date_1, evaluation_date_2, evaluation_date_3 de la BD si existen; "
        "si no existen, deja esas celdas vacías.\n"
    )


def build_paragraph_width_rules() -> str:
    """Reglas para que el texto ocupe todo el ancho de la celda/campo."""
    return (
        "- ANCHO COMPLETO (OBLIGATORIO): cada párrafo narrativo debe ocupar el 100% del "
        "ancho útil de su celda o campo (de borde a borde). Alineación justificada "
        "(WD_ALIGN_PARAGRAPH.JUSTIFY); sin sangrías (left_indent/right_indent = 0); "
        "sin tabulaciones ni cuadros de texto estrechos.\n"
        "- Escribe en los párrafos de plantilla que ya tienen justificado; no crees párrafos "
        "nuevos alineados a la izquierda que dejen franjas vacías a la derecha.\n"
        "- Si un apartado tiene 2+ párrafos en la misma celda, cada párrafo va justificado "
        "y a ancho completo (usa \\n\\n y reutiliza párrafos vacíos de la plantilla).\n"
        "  Patrón Python:\n"
        "    from docx.enum.text import WD_ALIGN_PARAGRAPH\n"
        "    from docx.shared import Pt, Cm\n"
        "    def aplicar_ancho_completo(p):\n"
        "        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY\n"
        "        p.paragraph_format.left_indent = Cm(0)\n"
        "        p.paragraph_format.right_indent = Cm(0)\n"
        "        p.paragraph_format.first_line_indent = Cm(0)\n"
        "        p.paragraph_format.space_before = Pt(0)\n"
        "        p.paragraph_format.space_after = Pt(0)\n"
        + build_no_fabrication_rules()
    )


def build_redaction_min_paragraphs_rules() -> str:
    """Reglas de extensión mínima para textos narrativos del informe."""
    return (
        "- REDACCIÓN (OBLIGATORIO): cada apartado narrativo del Word debe tener "
        "como mínimo 2 párrafos completos (no una sola oración ni un solo bloque). "
        "Aplica a motivo de evaluación, diagnóstico, fortalezas, necesidades de apoyo "
        "(pedagógico, social/afectivo y salud), trabajo colaborativo, apoyos en el hogar, "
        "acuerdos y cualquier sección de desarrollo del rol.\n"
        "- Cada párrafo debe aportar información distinta (contexto + implicancia, "
        "observación + orientación, etc.). Separa párrafos con un solo salto de línea "
        "(\\n o w:br); no uses un único párrafo largo para cumplir extensión.\n"
        "- Antes de exportar, revisa que ningún campo narrativo quede con menos de 2 párrafos.\n"
        + build_paragraph_width_rules()
    )


def build_familia_form_rules(base_filename: str) -> str:
    return (
        f"- PLANTILLA FORMULARIO (OBLIGATORIO): usa «{base_filename}» como base del informe. "
        f"Copia ese archivo (shutil.copy) y trabaja sobre la copia. "
        "NO uses FORMATO INFORME DE FAMILIA.docx ni reconstruyas el documento.\n"
        "- La plantilla tiene campos de formulario Word (content controls; a veces muestran "
        "«Haz clic o pulse aquí para escribir texto»). Rellénalos sin mover tablas ni cambiar estilos.\n"
        "- Lee primero el expediente del estudiante (docx del caso, cartilla, etc.) y extrae los datos. "
        "Si el formulario ya trae identificación rellena, consérvala.\n"
        "- Mapeo de campos (tag w:sdt o placeholder → valor):\n"
        "    Estudiante: student_full_name / Nombres y Apellidos; "
        "student_identification_number / RUN / Rut (estudiante); "
        "student_born_date / Fecha nacimiento; student_age / Edad; "
        "student_course / Curso / Nivel; student_school / Establecimiento.\n"
        "    Profesional: professional_full_name / professional_social_name / Nombre; "
        "professional_identification_number / Rut (profesional); "
        "professional_role / Rol / cargo; professional_phone_email / Teléfono / E-mail; "
        "report_delivery_date / Fecha entrega de informe.\n"
        "    Receptor: receiver_full_name / Nombre; receiver_identification_number / Rut; "
        "receiver_relationship / Relación con el/la estudiante; "
        "receiver_presence_of / En presencia de.\n"
        "    Contenido: evaluation_reason / motivo; diagnosis / diagnostic; "
        "pedagogical_strengths / strengths_1; pedagogical_support_needs / support_needs_1; "
        "social_affective_strengths / strengths_2; social_affective_support_needs / support_needs_2; "
        "health_strengths / strengths_3; health_support_needs / support_needs_3; "
        "collaborative_work; home_based_description / home_support; "
        "school_family_agreements / agreements_commitments.\n"
        "- Nombre y Rut van en sus campos respectivos; el Rol/cargo NUNCA recibe el RUT.\n"
        "- Rellena con python-docx recorriendo w:sdt (w:tag) y asignando texto al w:sdtContent, "
        "o reemplazando {clave}, [clave] y <<clave>> en párrafos y celdas.\n"
        "- Patrón mínimo para content controls:\n"
        "    from docx import Document\n"
        "    from docx.oxml.ns import qn\n"
        "  def rellenar_formulario(ruta, reemplazos):\n"
        "      doc = Document(ruta)\n"
        "      def norm(s): return re.sub(r'[^a-z0-9]+','', (s or '').lower())\n"
        "      tags = {norm(k): str(v or '') for k,v in reemplazos.items()}\n"
        "      for sdt in doc.element.body.iter(qn('w:sdt')):\n"
        "          tag = sdt.find('.//'+qn('w:tag'))\n"
        "          if tag is None: continue\n"
        "          key = norm(tag.get(qn('w:val')))\n"
        "          if key not in tags: continue\n"
        "          content = sdt.find(qn('w:sdtContent'))\n"
        "          if content is None: continue\n"
        "          for t in content.iter(qn('w:t')): t.text = ''\n"
        "          ts = list(content.iter(qn('w:t')))\n"
        "          if ts: ts[0].text = tags[key]\n"
        "      for p in doc.paragraphs:\n"
        "          t = p.text\n"
        "          for k,v in reemplazos.items():\n"
        "              for fmt in ('{%s}','[%s]','<<%s>>'):\n"
        "                  t = t.replace(fmt % k, str(v or ''))\n"
        "          if t != p.text: p.text = t\n"
        "      for tbl in doc.tables:\n"
        "          for row in tbl.rows:\n"
        "              for cell in row.cells:\n"
        "                  for p in cell.paragraphs:\n"
        "                      t = p.text\n"
        "                      for k,v in reemplazos.items():\n"
        "                          for fmt in ('{%s}','[%s]','<<%s>>'):\n"
        "                              t = t.replace(fmt % k, str(v or ''))\n"
        "                      if t != p.text: p.text = t\n"
        "      doc.save(ruta)\n"
        "- Conserva tipografía y alineación de la plantilla; no uses cell.text sobre filas de rótulo.\n"
        + build_paragraph_width_rules()
    )
