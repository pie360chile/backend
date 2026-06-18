"""Detección y reglas de plantilla para informe a la familia del agente."""

from __future__ import annotations

import re
import unicodedata


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
    # Generado desde admin o plantilla PIE360 (no el formato ministerial vacío)
    if "informe familia" in lower or "informe_familia" in lower.replace(" ", "_"):
        if "formato" not in lower:
            return True
    return False


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


def pick_familia_base_template(file_names: list[str] | None) -> tuple[str | None, str]:
    """Devuelve (nombre_archivo, tipo) con tipo form | tabla | none."""
    names = file_names or []
    form = [n for n in names if is_familia_form_template(n)]
    tabla = [n for n in names if is_familia_tabla_template(n)]
    if form:
        form.sort(key=familia_form_template_priority)
        return form[0], "form"
    if tabla:
        return tabla[0], "tabla"
    return None, "none"


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
    )
