"""Exportación a Word del Formulario Único de Revaluación (documento 6).

Las plantillas oficiales `fur*_formulario.docx` traen un content control por cada
campo del formulario ministerial, etiquetado con la clave semántica del
`formData` del frontend (`full_name`, `nee_maintained__si`,
`participating_professionals[0].profession_id`, ...). Aquí se resuelven esos
valores desde `fur_forms` y se escriben en una copia de la plantilla.

Las casillas se conservan siempre visibles: sin marcar quedan como un cuadro
vacío y marcadas como un cuadro negro relleno, igual que si una persona las
hubiera marcado en Word.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Optional

from docx import Document
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from sqlalchemy.orm import Session

from app.backend.db.models import (
    CareerTypeModel,
    CourseModel,
    SchoolModel,
    StudentAcademicInfoModel,
    StudentPersonalInfoModel,
)
from app.backend.utils.professional_display import map_professional_id_to_display_name

W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"

TEMPLATES_DIRECTORY = Path("files/original_student_files")

FUR_TEMPLATE_BY_VARIANT: dict[str, str] = {
    "tel": "fur1_tel_formulario.docx",
    "tel_tl": "fur1_tel_formulario.docx",  # variante antigua, mismo formulario oficial
    "dea": "fur2_dep_formulario.docx",
    "tdah": "fur3_tda_formulario.docx",
    "neet": "fur4_ci_t_formulario.docx",
    "neep": "fur5_ci_p_formulario.docx",
    "discapacidad_motora": "fur6_dm_formulario.docx",
    "discapacidad_visual": "fur7_dv_formulario.docx",
    "discapacidad_auditiva": "fur8_da_formulario.docx",
    "discapacidad_multiple": "fur9_dmu_formulario.docx",
    "tea": "fur10_tea_formulario.docx",
    "disfasia": "fur11_dstc_formulario.docx",
}

FUR_FIELD_FONT_NAME = "Arial"
FUR_FIELD_FONT_HALF_POINTS = "20"  # 10 pt
FUR_FIELD_FONT_COLOR = "000000"  # negro

FUR_CHECKBOX_FONT = "MS Gothic"
# Las plantillas oficiales traen casillas entre 3 y 11 pt; se unifican para que
# ninguna quede ilegible en el Word exportado.
FUR_CHECKBOX_HALF_POINTS = "20"  # 10 pt
FUR_CHECKED_CHAR = "\u25a0"  # ■ cuadro relleno
FUR_UNCHECKED_CHAR = "\u2610"  # ☐ cuadro vacío
FUR_CHECKED_STATE_HEX = "25A0"
FUR_UNCHECKED_STATE_HEX = "2610"

_TRUE_WORDS = {"1", "true", "si", "x", "yes", "checked", "marcado"}
_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_PATH_SEGMENT = re.compile(r"^([A-Za-z0-9_]+)(?:\[(\d+)\])?$")

_PROFESSIONAL_ID_KEYS = {"professional_id"}
_CAREER_TYPE_ID_KEYS = {"profession_id", "profession_specialty_id", "career_type_id"}

# CT_RPr define un orden fijo de hijos; Word rechaza propiedades fuera de secuencia.
_RPR_ORDER = (
    "w:rStyle",
    "w:rFonts",
    "w:b",
    "w:bCs",
    "w:i",
    "w:iCs",
    "w:caps",
    "w:smallCaps",
    "w:strike",
    "w:dstrike",
    "w:outline",
    "w:shadow",
    "w:emboss",
    "w:imprint",
    "w:noProof",
    "w:snapToGrid",
    "w:vanish",
    "w:webHidden",
    "w:color",
    "w:spacing",
    "w:w",
    "w:kern",
    "w:position",
    "w:sz",
    "w:szCs",
    "w:highlight",
    "w:u",
    "w:effect",
    "w:bdr",
    "w:shd",
    "w:fitText",
    "w:vertAlign",
    "w:rtl",
    "w:cs",
    "w:em",
    "w:lang",
    "w:eastAsianLayout",
    "w:specVanish",
    "w:oMath",
)


# --------------------------------------------------------------------------- #
# Helpers XML
# --------------------------------------------------------------------------- #
def ensure_rpr(parent, position: int = 0):
    """Devuelve el `w:rPr` de `parent`, creándolo si falta."""
    rpr = parent.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        parent.insert(position, rpr)
    return rpr


def _insert_ordered(rpr, name: str):
    for existing in rpr.findall(qn(name)):
        rpr.remove(existing)
    element = OxmlElement(name)
    index = _RPR_ORDER.index(name)
    for child in rpr:
        for candidate in _RPR_ORDER[index:]:
            if child.tag == qn(candidate):
                child.addprevious(element)
                return element
    rpr.append(element)
    return element


def apply_field_font(
    rpr,
    font_name: str = FUR_FIELD_FONT_NAME,
    half_points: str = FUR_FIELD_FONT_HALF_POINTS,
    east_asia: bool = False,
) -> None:
    """Fija tipografía, tamaño y color del campo (por defecto Arial 10 negro).

    `east_asia` se usa en las casillas, cuyo símbolo se dibuja con la tipografía
    CJK declarada por el propio control.
    """
    fonts = _insert_ordered(rpr, "w:rFonts")
    attributes = ["w:ascii", "w:hAnsi", "w:cs"]
    if east_asia:
        attributes.append("w:eastAsia")
    for attr in attributes:
        fonts.set(qn(attr), font_name)
    if not east_asia and fonts.get(qn("w:eastAsia")) is not None:
        del fonts.attrib[qn("w:eastAsia")]
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme"):
        if fonts.get(qn(attr)) is not None:
            del fonts.attrib[qn(attr)]
    if half_points:
        for name in ("w:sz", "w:szCs"):
            _insert_ordered(rpr, name).set(qn("w:val"), half_points)
    _insert_ordered(rpr, "w:color").set(qn("w:val"), FUR_FIELD_FONT_COLOR)
    # El estilo de marcador de posición pinta el texto en gris; el contenido ya
    # no es un marcador.
    for style in rpr.findall(qn("w:rStyle")):
        value = (style.get(qn("w:val")) or "").lower()
        if "marcadordeposicin" in value or "placeholdertext" in value:
            rpr.remove(style)


def apply_checkbox_font(rpr) -> None:
    apply_field_font(rpr, FUR_CHECKBOX_FONT, FUR_CHECKBOX_HALF_POINTS, east_asia=True)


def _w14(name: str) -> str:
    return f"{{{W14_NS}}}{name}"


def _find_checkbox(sdt_pr):
    for child in sdt_pr:
        if child.tag == _w14("checkbox") or child.tag.endswith("}checkbox"):
            return child
    return None


def is_checkbox_control(sdt_pr) -> bool:
    return _find_checkbox(sdt_pr) is not None


def normalize_checkbox_states(sdt_pr) -> bool:
    """Deja el estado marcado como cuadro negro relleno y el vacío como cuadro.

    Se aplica sobre el propio control, así el símbolo es el mismo cuando el
    sistema marca la casilla y cuando alguien la marca a mano en Word.
    """
    checkbox = _find_checkbox(sdt_pr)
    if checkbox is None:
        return False
    for name, hex_value in (
        ("checkedState", FUR_CHECKED_STATE_HEX),
        ("uncheckedState", FUR_UNCHECKED_STATE_HEX),
    ):
        element = next(
            (child for child in checkbox if child.tag.endswith("}" + name)),
            None,
        )
        if element is None:
            element = parse_xml(
                f'<w14:{name} xmlns:w14="{W14_NS}" '
                f'w14:val="{hex_value}" w14:font="{FUR_CHECKBOX_FONT}"/>'
            )
            checkbox.append(element)
            continue
        element.set(_w14("val"), hex_value)
        element.set(_w14("font"), FUR_CHECKBOX_FONT)
    return True


def _state_symbol(sdt_pr, checked: bool) -> tuple[str, str]:
    """Símbolo y tipografía declarados por el control para el estado pedido."""
    checkbox = _find_checkbox(sdt_pr)
    name = "checkedState" if checked else "uncheckedState"
    fallback = FUR_CHECKED_CHAR if checked else FUR_UNCHECKED_CHAR
    if checkbox is None:
        return fallback, FUR_CHECKBOX_FONT
    element = next((child for child in checkbox if child.tag.endswith("}" + name)), None)
    if element is None:
        return fallback, FUR_CHECKBOX_FONT
    font = element.get(_w14("font")) or FUR_CHECKBOX_FONT
    raw = element.get(_w14("val")) or ""
    try:
        return chr(int(raw, 16)), font
    except ValueError:
        return fallback, font


def _content_runs(sdt) -> list:
    content = sdt.find(qn("w:sdtContent"))
    if content is None:
        return []
    return list(content.iter(qn("w:r")))


def _write_run_text(run, text: str) -> None:
    """Deja el run con un único texto; los saltos de línea se vuelven `w:br`."""
    for child in list(run):
        if child.tag != qn("w:rPr"):
            run.remove(child)
    lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for index, line in enumerate(lines):
        if index:
            run.append(OxmlElement("w:br"))
        node = OxmlElement("w:t")
        node.set(qn("xml:space"), "preserve")
        node.text = line
        run.append(node)


def _set_checkbox_state(sdt, sdt_pr, checked: bool) -> None:
    checkbox = _find_checkbox(sdt_pr)
    if checkbox is None:
        return
    checked_el = next((child for child in checkbox if child.tag.endswith("}checked")), None)
    if checked_el is None:
        checked_el = parse_xml(f'<w14:checked xmlns:w14="{W14_NS}" w14:val="0"/>')
        checkbox.insert(0, checked_el)
    checked_el.set(_w14("val"), "1" if checked else "0")

    symbol, font = _state_symbol(sdt_pr, checked)
    runs = _content_runs(sdt)
    if not runs:
        return
    run = runs[0]
    apply_field_font(ensure_rpr(run), font, FUR_CHECKBOX_HALF_POINTS, east_asia=True)
    _write_run_text(run, symbol)
    for extra in runs[1:]:
        extra.getparent().remove(extra)


def _set_control_text(sdt, sdt_pr, text: str) -> None:
    for placeholder in sdt_pr.findall(qn("w:showingPlcHdr")):
        sdt_pr.remove(placeholder)
    runs = _content_runs(sdt)
    if not runs:
        return
    run = runs[0]
    apply_field_font(ensure_rpr(run))
    _write_run_text(run, text)
    for extra in runs[1:]:
        extra.getparent().remove(extra)


def relax_fixed_row_heights(document: Document) -> int:
    """Convierte las alturas de fila fijas en alturas mínimas.

    Las plantillas ministeriales traen filas con `hRule="exact"`, que recortan el
    texto que no cabe (RUN, correos y registros profesionales quedaban a medias).
    Con `atLeast` la fila conserva su alto original cuando está vacía y crece si
    el contenido lo necesita.
    """
    relaxed = 0
    for height in document.element.body.iter(qn("w:trHeight")):
        if (height.get(qn("w:hRule")) or "").lower() == "exact":
            height.set(qn("w:hRule"), "atLeast")
            relaxed += 1
    return relaxed


def iter_content_controls(document: Document):
    """Recorre los `w:sdt` del cuerpo, encabezados y pies del documento."""
    roots = [document.element.body]
    for section in document.sections:
        for part in (
            section.header,
            section.first_page_header,
            section.even_page_header,
            section.footer,
            section.first_page_footer,
            section.even_page_footer,
        ):
            element = getattr(part, "_element", None)
            if element is not None:
                roots.append(element)
    for root in roots:
        for sdt in root.iter(qn("w:sdt")):
            sdt_pr = sdt.find(qn("w:sdtPr"))
            if sdt_pr is None:
                continue
            tag_el = sdt_pr.find(qn("w:tag"))
            tag = (tag_el.get(qn("w:val")) or "").strip() if tag_el is not None else ""
            if not tag:
                continue
            yield sdt, sdt_pr, tag


# --------------------------------------------------------------------------- #
# Resolución de valores
# --------------------------------------------------------------------------- #
def _normalize(value: Any) -> str:
    text = str(value if value is not None else "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _lookup(data: Mapping[str, Any], path: str) -> Any:
    current: Any = data
    for raw in path.split("."):
        matched = _PATH_SEGMENT.match(raw)
        if matched is None:
            return None
        if not isinstance(current, Mapping):
            return None
        current = current.get(matched.group(1))
        index = matched.group(2)
        if index is not None:
            if not isinstance(current, (list, tuple)):
                return None
            position = int(index)
            current = current[position] if 0 <= position < len(current) else None
        if current is None:
            return None
    return current


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return _normalize(value) in _TRUE_WORDS


def checkbox_is_checked(tag: str, data: Mapping[str, Any]) -> bool:
    """Resuelve el estado de una casilla a partir de su etiqueta semántica.

    `clave` se lee como booleano y `clave__valor` como opción de un grupo
    (`nee_maintained__si`, `revaluation_type__proceso`, ...).
    """
    key, separator, expected = tag.rpartition("__")
    if not separator or not key:
        return _as_bool(_lookup(data, tag))
    value = _lookup(data, key)
    if value is None:
        return _as_bool(_lookup(data, tag))
    if isinstance(value, bool):
        return value and _normalize(expected) in _TRUE_WORDS
    if isinstance(value, (list, tuple, set)):
        return any(_normalize(item) == _normalize(expected) for item in value)
    return _normalize(value) == _normalize(expected)


def _format_date(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.strftime("%d/%m/%Y")
    text = str(value).strip()
    matched = _ISO_DATE.match(text)
    if matched:
        return f"{matched.group(3)}/{matched.group(2)}/{matched.group(1)}"
    return text


def control_text(tag: str, data: Mapping[str, Any]) -> str:
    value = _lookup(data, tag)
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return _format_date(value)


# --------------------------------------------------------------------------- #
# Datos del formulario
# --------------------------------------------------------------------------- #
def _calculate_age(born: Any) -> str:
    if isinstance(born, (datetime, date)):
        birth = born if isinstance(born, date) and not isinstance(born, datetime) else born.date()
    else:
        matched = _ISO_DATE.match(str(born or "").strip())
        if not matched:
            return ""
        birth = date(int(matched.group(1)), int(matched.group(2)), int(matched.group(3)))
    today = date.today()
    years = today.year - birth.year
    months = today.month - birth.month
    if today.day < birth.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    if years < 0:
        return ""
    if years == 0:
        return "1 mes" if months == 1 else f"{months} meses"
    year_text = "1 año" if years == 1 else f"{years} años"
    if months == 0:
        return year_text
    month_text = "1 mes" if months == 1 else f"{months} meses"
    return f"{year_text} {month_text}"


def _student_identification(db: Session, student_id: int) -> dict[str, Any]:
    """Datos que el formulario muestra como solo lectura desde la ficha."""
    personal = (
        db.query(StudentPersonalInfoModel)
        .filter(StudentPersonalInfoModel.student_id == student_id)
        .first()
    )
    academic = (
        db.query(StudentAcademicInfoModel)
        .filter(StudentAcademicInfoModel.student_id == student_id)
        .first()
    )
    out: dict[str, Any] = {}
    if personal is not None:
        full_name = " ".join(
            part
            for part in (
                (personal.names or "").strip(),
                (personal.father_lastname or "").strip(),
                (personal.mother_lastname or "").strip(),
            )
            if part
        )
        out["full_name"] = full_name
        out["identification_number"] = (personal.identification_number or "").strip()
        out["born_date"] = _format_date(personal.born_date)
        out["age"] = _calculate_age(personal.born_date)
    if academic is not None and academic.course_id:
        course = db.query(CourseModel).filter(CourseModel.id == academic.course_id).first()
        if course is not None:
            out["current_course"] = (course.course_name or "").strip()
    return {key: value for key, value in out.items() if value}


def _school_identification(db: Session, school_id: Optional[int]) -> dict[str, Any]:
    if not school_id:
        return {}
    school = db.query(SchoolModel).filter(SchoolModel.id == school_id).first()
    if school is None:
        return {}
    out = {
        "establishment_name": (school.school_name or "").strip(),
        "director_name": (school.director_name or "").strip(),
    }
    return {key: value for key, value in out.items() if value}


def _career_type_names(db: Session, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = db.query(CareerTypeModel).filter(CareerTypeModel.id.in_(ids)).all()
    return {int(row.id): (row.career_type or "").strip() for row in rows}


def _collect_ids(node: Any, professional_ids: set[int], career_ids: set[int]) -> None:
    if isinstance(node, Mapping):
        for key, value in node.items():
            if isinstance(value, (Mapping, list, tuple)):
                _collect_ids(value, professional_ids, career_ids)
                continue
            try:
                numeric = int(value)
            except (TypeError, ValueError):
                continue
            if key in _PROFESSIONAL_ID_KEYS:
                professional_ids.add(numeric)
            elif key in _CAREER_TYPE_ID_KEYS:
                career_ids.add(numeric)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _collect_ids(item, professional_ids, career_ids)


def _replace_ids(node: Any, professionals: Mapping[int, str], careers: Mapping[int, str]) -> Any:
    if isinstance(node, Mapping):
        out: dict[str, Any] = {}
        for key, value in node.items():
            if isinstance(value, (Mapping, list, tuple)):
                out[key] = _replace_ids(value, professionals, careers)
                continue
            try:
                numeric = int(value)
            except (TypeError, ValueError):
                out[key] = value
                continue
            if key in _PROFESSIONAL_ID_KEYS:
                out[key] = professionals.get(numeric) or value
            elif key in _CAREER_TYPE_ID_KEYS:
                out[key] = careers.get(numeric) or value
            else:
                out[key] = value
        return out
    if isinstance(node, (list, tuple)):
        return [_replace_ids(item, professionals, careers) for item in node]
    return node


def build_fur_data(db: Session, student_id: int, fur_record: Mapping[str, Any]) -> dict[str, Any]:
    """Aplana el registro FUR y resuelve IDs, cursos y datos de la ficha."""
    professional_ids: set[int] = set()
    career_ids: set[int] = set()
    _collect_ids(fur_record, professional_ids, career_ids)
    professionals = map_professional_id_to_display_name(db, sorted(professional_ids))
    careers = _career_type_names(db, career_ids)
    data = _replace_ids(dict(fur_record), professionals, careers)

    defaults = _student_identification(db, student_id)
    defaults.update(_school_identification(db, fur_record.get("school_id")))
    for key, value in defaults.items():
        if not str(data.get(key) or "").strip():
            data[key] = value
    if not str(data.get("current_year") or "").strip():
        data["current_year"] = date.today().year
    return data


# --------------------------------------------------------------------------- #
# Generación
# --------------------------------------------------------------------------- #
def resolve_template_path(fur_variant: Optional[str], base_directory: Optional[Path] = None) -> Optional[Path]:
    filename = FUR_TEMPLATE_BY_VARIANT.get(str(fur_variant or "").strip())
    if not filename:
        return None
    return (base_directory or TEMPLATES_DIRECTORY) / filename


def fill_fur_docx(template_path: Path, data: Mapping[str, Any], output_path: Path) -> dict[str, Any]:
    """Escribe `data` en los content controls de la plantilla FUR."""
    document = Document(str(template_path))
    filled: list[str] = []
    empty: list[str] = []
    checked: list[str] = []
    relaxed_rows = relax_fixed_row_heights(document)

    for sdt, sdt_pr, tag in iter_content_controls(document):
        if is_checkbox_control(sdt_pr):
            normalize_checkbox_states(sdt_pr)
            state = checkbox_is_checked(tag, data)
            _set_checkbox_state(sdt, sdt_pr, state)
            if state:
                checked.append(tag)
            continue
        text = control_text(tag, data)
        _set_control_text(sdt, sdt_pr, text)
        (filled if text else empty).append(tag)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))
    return {
        "status": "success",
        "file_path": str(output_path),
        "filename": output_path.name,
        "text_filled": len(filled),
        "text_empty": len(empty),
        "checkboxes_checked": len(checked),
        "relaxed_rows": relaxed_rows,
        "empty_tags": sorted(empty),
    }


def generate_fur_docx(
    db: Session,
    student_id: int,
    fur_record: Mapping[str, Any],
    output_directory: str = "files/system/students",
    templates_directory: Optional[Path] = None,
) -> dict[str, Any]:
    """Genera el Word del FUR a partir del registro guardado en `fur_forms`."""
    fur_variant = str(fur_record.get("fur_variant") or "").strip()
    template_path = resolve_template_path(fur_variant, templates_directory)
    if template_path is None:
        return {
            "status": "error",
            "message": f"No hay plantilla oficial asociada al tipo de FUR '{fur_variant}'.",
        }
    if not template_path.is_file():
        return {
            "status": "error",
            "message": f"No se encontró la plantilla del FUR: {template_path.name}",
        }

    data = build_fur_data(db, student_id, fur_record)
    safe_name = re.sub(r"[^\w-]+", "_", str(data.get("full_name") or f"estudiante_{student_id}")).strip("_")[:40]
    output_path = Path(output_directory) / f"fur_{fur_variant}_{safe_name}_{uuid.uuid4().hex[:8]}.docx"
    return fill_fur_docx(template_path, data, output_path)
