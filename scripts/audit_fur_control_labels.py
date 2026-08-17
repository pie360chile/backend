"""Audita las etiquetas de los content controls de los FUR contra el texto del Word.

Para cada control muestra el texto que lo precede y lo sigue dentro de su celda,
más los encabezados de las filas anteriores. Con eso se puede verificar que la
clave semántica asignada corresponde al campo real de la plantilla oficial.

    python scripts/audit_fur_control_labels.py                  # resumen de los 11
    python scripts/audit_fur_control_labels.py fur2_dep 70 100   # detalle por ordinal
    python scripts/audit_fur_control_labels.py --dump            # reporte completo a disco
"""

from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.backend.utils.fur_docx_export import is_checkbox_control  # noqa: E402

TEMPLATES_DIR = ROOT / "files" / "original_student_files"
REPORT_DIR = TEMPLATES_DIR / "fur_label_audit"
PLACEHOLDER = "Escriba aquí"
BEFORE_CHARS = 170
AFTER_CHARS = 90


def _clean(text: str) -> str:
    return " ".join((text or "").replace(PLACEHOLDER, " ").split())


def _element_text(element) -> str:
    return _clean(" ".join(node.text or "" for node in element.iter(qn("w:t"))))


def _enclosing(node, tag: str):
    while node is not None and node.tag != qn(tag):
        node = node.getparent()
    return node


def _container(sdt):
    """Celda que contiene el control; si no está en tabla, el párrafo."""
    cell = _enclosing(sdt, "w:tc")
    if cell is not None:
        return cell
    return _enclosing(sdt, "w:p")


def _split_context(container, sdt) -> tuple[str, str]:
    """Texto del contenedor antes y después del control, sin el propio control."""
    before: list[str] = []
    after: list[str] = []
    seen = False
    for node in container.iter(qn("w:sdt"), qn("w:t")):
        if node is sdt:
            seen = True
            continue
        # El texto interno de otro control se atribuye a ese control, no a este.
        if node.tag == qn("w:sdt"):
            continue
        if _enclosing(node, "w:sdt") is not None and _enclosing(node, "w:sdt") is not sdt:
            marker = "[ ]"
            (after if seen else before).append(marker)
            continue
        (after if seen else before).append(node.text or "")
    return _clean("".join(before)), _clean("".join(after))


def _previous_rows(container, rows: int = 3) -> list[str]:
    row = _enclosing(container, "w:tr")
    if row is None:
        return []
    table = row.getparent()
    if table is None:
        return []
    all_rows = table.findall(qn("w:tr"))
    try:
        index = all_rows.index(row)
    except ValueError:
        return []
    out: list[str] = []
    for previous in reversed(all_rows[max(0, index - rows) : index]):
        text = _element_text(previous)
        if text:
            out.append(text)
    return out


def controls(path: Path) -> list[dict]:
    document = Document(str(path))
    out: list[dict] = []
    ordinal = 0
    for sdt in document.element.body.iter(qn("w:sdt")):
        sdt_pr = sdt.find(qn("w:sdtPr"))
        if sdt_pr is None:
            continue
        tag_el = sdt_pr.find(qn("w:tag"))
        if tag_el is None:
            continue
        ordinal += 1
        container = _container(sdt)
        before, after = _split_context(container, sdt) if container is not None else ("", "")
        out.append(
            {
                "ordinal": ordinal,
                "tag": tag_el.get(qn("w:val")) or "",
                "kind": "casilla" if is_checkbox_control(sdt_pr) else "texto",
                "before": before,
                "after": after,
                "previous_rows": _previous_rows(container) if container is not None else [],
            }
        )
    return out


def _render(item: dict) -> str:
    lines = [f"[{item['ordinal']:3d}] {item['kind']:7s} {item['tag']}"]
    for text in item["previous_rows"]:
        lines.append(f"        fila previa: {text[:150]}")
    lines.append(f"        antes: {item['before'][-BEFORE_CHARS:]}")
    lines.append(f"        despues: {item['after'][:AFTER_CHARS]}")
    return "\n".join(lines)


def detail(stem: str, first: int, last: int) -> None:
    path = TEMPLATES_DIR / f"{stem}_formulario.docx"
    for item in controls(path):
        if first <= item["ordinal"] <= last:
            print(_render(item))


def dump() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(TEMPLATES_DIR.glob("fur*_formulario.docx")):
        items = controls(path)
        report = REPORT_DIR / f"{path.stem}.txt"
        report.write_text(
            f"{path.name} — {len(items)} controles\n\n"
            + "\n".join(_render(item) for item in items)
            + "\n",
            encoding="utf-8",
        )
        print(f"{report.name}: {len(items)} controles")


def summary() -> None:
    """Marca los controles cuya celda es un encabezado 'RUN estudiante:'."""
    total = 0
    for path in sorted(TEMPLATES_DIR.glob("fur*_formulario.docx")):
        wrong = [
            item["tag"]
            for item in controls(path)
            if item["before"].lower().startswith("run estudiante")
            and item["tag"] != "identification_number"
        ]
        total += len(wrong)
        print(f"{path.name}: {len(wrong)} {wrong}")
    print(f"\nControles mal etiquetados en celdas 'RUN estudiante': {total}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--dump":
        dump()
    elif len(sys.argv) >= 2:
        detail(
            sys.argv[1],
            int(sys.argv[2]) if len(sys.argv) > 2 else 1,
            int(sys.argv[3]) if len(sys.argv) > 3 else 10_000,
        )
    else:
        summary()
