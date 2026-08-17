"""Normaliza la apariencia de los campos de los FUR `*_formulario.docx`.

- Campos de texto en Arial 10 negro (también lo que se escriba después en Word).
- Casillas: cuadro vacío sin marcar y cuadro negro relleno al marcarlas, todas
  del mismo tamaño.
- Filas de altura fija convertidas en altura mínima, para que no recorten texto.

    python scripts/set_fur_control_font.py
    python scripts/set_fur_control_font.py --only fur5_ci_p.doc
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.backend.utils.fur_docx_export import (  # noqa: E402
    apply_checkbox_font,
    apply_field_font,
    ensure_rpr,
    is_checkbox_control,
    iter_content_controls,
    normalize_checkbox_states,
    relax_fixed_row_heights,
)
from fur_semantic_field_maps import EXPECTED_COUNTS  # noqa: E402

TEMPLATES_DIR = ROOT / "files" / "original_student_files"


def restyle(path: Path) -> dict[str, int]:
    document = Document(str(path))
    stats = {"text": 0, "checkbox": 0, "runs": 0}
    stats["rows"] = relax_fixed_row_heights(document)

    for sdt, sdt_pr, _tag in iter_content_controls(document):
        if is_checkbox_control(sdt_pr):
            normalize_checkbox_states(sdt_pr)
            apply_checkbox_font(ensure_rpr(sdt_pr))
            content = sdt.find(qn("w:sdtContent"))
            if content is not None:
                for run in content.iter(qn("w:r")):
                    apply_checkbox_font(ensure_rpr(run))
            stats["checkbox"] += 1
            continue

        apply_field_font(ensure_rpr(sdt_pr))
        content = sdt.find(qn("w:sdtContent"))
        if content is not None:
            for run in content.iter(qn("w:r")):
                apply_field_font(ensure_rpr(run))
                stats["runs"] += 1
            # Marca de párrafo: lo que se escriba en un campo vacío hereda Arial 10.
            for paragraph in content.iter(qn("w:p")):
                p_pr = paragraph.find(qn("w:pPr"))
                if p_pr is None:
                    p_pr = OxmlElement("w:pPr")
                    paragraph.insert(0, p_pr)
                apply_field_font(ensure_rpr(p_pr, position=len(p_pr)))
        stats["text"] += 1

    document.save(str(path))
    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Procesa un solo origen, p. ej. fur5_ci_p.doc")
    args = parser.parse_args()

    selected = [
        name
        for name in EXPECTED_COUNTS
        if args.only is None or name.lower() == args.only.lower()
    ]
    if not selected:
        raise SystemExit(f"FUR desconocido: {args.only}")

    for source in selected:
        path = TEMPLATES_DIR / source.replace(".doc", "_formulario.docx")
        if not path.is_file():
            raise SystemExit(f"Falta el formulario generado: {path}")
        stats = restyle(path)
        print(
            f"{path.name}: texto={stats['text']} runs={stats['runs']} "
            f"casillas={stats['checkbox']} filas_liberadas={stats['rows']}"
        )


if __name__ == "__main__":
    main()
