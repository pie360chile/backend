"""Aplica las claves semánticas a los content controls de los *_formulario.docx.

Recorre los controles en orden de documento y reescribe Tag y Title (alias) con
la clave de `formData` que corresponde según `fur_semantic_field_maps`. Escribe
el XML directamente con python-docx: Word ignora los cambios de Tag/Title en un
Save() normal sobre estos archivos.

    python scripts/apply_fur_semantic_tags.py
    python scripts/apply_fur_semantic_tags.py --only fur5_ci_p.doc
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from fur_semantic_field_maps import EXPECTED_COUNTS, FUR_SEMANTIC_MAPS

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "files" / "original_student_files"
SEMANTIC_MANIFEST = TEMPLATES_DIR / "fur_semantic_controls_manifest.json"


def _semantic_tag(entry: dict) -> str:
    key = entry["key"]
    if entry.get("kind") == "checkbox" and entry.get("value") is not None:
        return f"{key}__{entry['value']}"
    return key


def _validate_maps() -> None:
    for source, expected in EXPECTED_COUNTS.items():
        mapped = FUR_SEMANTIC_MAPS[source]
        missing = [i for i in range(1, expected + 1) if i not in mapped]
        extra = [i for i in mapped if i < 1 or i > expected]
        if missing or extra:
            raise ValueError(
                f"{source}: faltan={missing[:10]} sobran={extra[:10]} "
                f"(mapeados={len(mapped)} esperados={expected})"
            )


def _set_val(parent, tag: str, value: str) -> None:
    element = parent.find(qn(tag))
    if element is None:
        element = parent.makeelement(qn(tag), {})
        parent.insert(0, element)
    element.set(qn("w:val"), value)


def _apply_to_document(source_name: str) -> dict:
    mapping = FUR_SEMANTIC_MAPS[source_name]
    output = TEMPLATES_DIR / source_name.replace(".doc", "_formulario.docx")
    document = Document(str(output))

    renamed: list[dict] = []
    failures: list[dict] = []
    ordinal = 0
    for sdt in document.element.body.iter(qn("w:sdt")):
        sdt_pr = sdt.find(qn("w:sdtPr"))
        if sdt_pr is None or sdt_pr.find(qn("w:tag")) is None:
            continue
        ordinal += 1
        current = sdt_pr.find(qn("w:tag")).get(qn("w:val")) or ""
        entry = mapping.get(ordinal)
        if entry is None:
            failures.append({"ordinal": ordinal, "tag": current, "error": "sin mapa semántico"})
            continue
        new_tag = _semantic_tag(entry)
        _set_val(sdt_pr, "w:tag", new_tag)
        _set_val(sdt_pr, "w:alias", new_tag)
        renamed.append(
            {
                "ordinal": ordinal,
                "old_tag": current,
                "tag": new_tag,
                "key": entry["key"],
                "kind": entry["kind"],
                "value": entry.get("value"),
                "changed": current != new_tag,
            }
        )

    expected = EXPECTED_COUNTS[source_name]
    if ordinal != expected:
        raise ValueError(f"{source_name}: {ordinal} controles en el .docx, se esperaban {expected}")

    document.save(str(output))
    return {
        "source": source_name,
        "output": output.name,
        "controls": ordinal,
        "renamed": len(renamed),
        "changed": sum(1 for item in renamed if item["changed"]),
        "failures": failures,
        "fields": renamed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Procesar un solo origen, p. ej. fur5_ci_p.doc")
    args = parser.parse_args()

    _validate_maps()
    selected = [
        name for name in EXPECTED_COUNTS if args.only is None or name.lower() == args.only.lower()
    ]
    if not selected:
        raise SystemExit(f"Archivo FUR desconocido: {args.only}")

    reports = []
    for source in selected:
        report = _apply_to_document(source)
        reports.append(report)
        print(
            f"{report['output']}: controles={report['controls']} "
            f"modificados={report['changed']} fallos={len(report['failures'])}"
        )

    manifest = {
        "templates_directory": str(TEMPLATES_DIR),
        "documents": reports,
        "total_renamed": sum(item["renamed"] for item in reports),
        "total_changed": sum(item["changed"] for item in reports),
        "total_failures": sum(len(item["failures"]) for item in reports),
    }
    SEMANTIC_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Manifiesto: {SEMANTIC_MANIFEST}")


if __name__ == "__main__":
    main()
