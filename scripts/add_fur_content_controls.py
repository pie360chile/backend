"""Convert the 11 official FUR .doc files to .docx with modern form controls.

The original ministerial files are password-protected legacy Word forms. This
script never overwrites them: it creates ``*_formulario.docx`` copies, removes
the document-level editing restriction from those copies and wraps every
legacy text/checkbox FormField in a tagged Content Control.

Run on Windows with Microsoft Word installed:

    python scripts/add_fur_content_controls.py
    python scripts/add_fur_content_controls.py --only fur5_ci_p.doc
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import win32com.client


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "files" / "original_student_files"
MANIFEST_PATH = TEMPLATES_DIR / "fur_content_controls_manifest.json"

WORD_DOCX_FORMAT = 16
WORD_TEXT_FORM_FIELD = 70
WORD_CHECKBOX_FORM_FIELD = 71
WORD_RICH_TEXT_CONTENT_CONTROL = 0
WORD_CHECKBOX_CONTENT_CONTROL = 8

FUR_FILES = (
    "fur1_tel.doc",
    "fur2_dep.doc",
    "fur3_tda.doc",
    "fur4_ci_t.doc",
    "fur5_ci_p.doc",
    "fur6_dm.doc",
    "fur7_dv.doc",
    "fur8_da.doc",
    "fur9_dmu.doc",
    "fur10_tea.doc",
    "fur11_dstc.doc",
)


def _fur_number(filename: str) -> int:
    match = re.match(r"fur(\d+)", filename, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Cannot determine FUR number from {filename}")
    return int(match.group(1))


def _output_path(source: Path) -> Path:
    return source.with_name(f"{source.stem}_formulario.docx")


def _remove_docx_protection(path: Path) -> bool:
    """Remove w:documentProtection from a generated copy."""
    member = "word/settings.xml"
    with zipfile.ZipFile(path, "r") as source_zip:
        entries = [(item, source_zip.read(item.filename)) for item in source_zip.infolist()]
        settings = next(payload for item, payload in entries if item.filename == member)
        replacement, substitutions = re.subn(
            rb"<w:documentProtection\b[^>]*/>",
            b"",
            settings,
            count=1,
        )
        if substitutions == 0:
            return False

        fd, temp_name = tempfile.mkstemp(suffix=".docx", dir=str(path.parent))
        os.close(fd)
        temp_path = Path(temp_name)
        with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as target_zip:
            for item, original_payload in entries:
                payload = replacement if item.filename == member else original_payload
                target_zip.writestr(item, payload)
    try:
        os.chmod(path, 0o666)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)
    return True


def _clean_context(text: str) -> str:
    text = text.replace("\r", " ").replace("\a", " ").replace("\x15", " ")
    return re.sub(r"\s+", " ", text).strip()


def _field_context(document: Any, start: int, end: int, radius: int = 180) -> str:
    doc_end = int(document.Content.End)
    context_range = document.Range(max(0, start - radius), min(doc_end, end + radius))
    return _clean_context(str(context_range.Text or ""))


def _field_tag(fur_number: int, index: int, field_type: int) -> str:
    kind = "checkbox" if field_type == WORD_CHECKBOX_FORM_FIELD else "text"
    return f"fur{fur_number}_{kind}_{index:03d}"


def _convert_to_docx(word: Any, source: Path, target: Path) -> None:
    document = word.Documents.Open(str(source), False, True)
    try:
        document.SaveAs2(str(target), WORD_DOCX_FORMAT)
    finally:
        document.Close(False)


def _add_controls(word: Any, target: Path, fur_number: int) -> dict[str, Any]:
    document = word.Documents.Open(str(target), False, False)
    fields: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    try:
        # SaveAs2 preserves the old compatibility mode; ContentControls cannot
        # be inserted until Word upgrades the generated copy.
        if int(document.CompatibilityMode) < 15:
            document.Convert()
        legacy_count = int(document.FormFields.Count)
        snapshots: list[dict[str, Any]] = []
        for index in range(1, legacy_count + 1):
            field = document.FormFields.Item(index)
            snapshots.append(
                {
                    "index": index,
                    "legacy_name": str(field.Name or ""),
                    "type": int(field.Type),
                    "start": int(field.Range.Start),
                    "end": int(field.Range.End),
                    "context": _field_context(
                        document,
                        int(field.Range.Start),
                        int(field.Range.End),
                    ),
                }
            )

        # Reverse order keeps the stored document positions stable.
        for snapshot in reversed(snapshots):
            index = snapshot["index"]
            field_type = snapshot["type"]
            tag = _field_tag(fur_number, index, field_type)
            try:
                field = document.FormFields.Item(index)
                start = int(field.Range.Start)
                field.Delete()
                insertion_range = document.Range(start, start)
                control_type = (
                    WORD_CHECKBOX_CONTENT_CONTROL
                    if field_type == WORD_CHECKBOX_FORM_FIELD
                    else WORD_RICH_TEXT_CONTENT_CONTROL
                )
                control = document.ContentControls.Add(control_type, insertion_range)
                control.Title = tag
                control.Tag = tag
                control.LockContentControl = False
                control.LockContents = False
                if field_type == WORD_TEXT_FORM_FIELD:
                    control.SetPlaceholderText(None, None, "Escriba aquí")
                fields.append({**snapshot, "tag": tag})
            except Exception as exc:  # COM errors contain useful Word details
                failures.append({**snapshot, "tag": tag, "error": str(exc)})

        document.Save()
        return {
            "source": target.name.replace("_formulario.docx", ".doc"),
            "output": target.name,
            "legacy_form_fields": legacy_count,
            "content_controls": int(document.ContentControls.Count),
            "fields": sorted(fields, key=lambda item: item["index"]),
            "failures": sorted(failures, key=lambda item: item["index"]),
        }
    finally:
        document.Close(False)


def generate(only: str | None = None) -> dict[str, Any]:
    selected = [name for name in FUR_FILES if only is None or name.lower() == only.lower()]
    if not selected:
        raise ValueError(f"Unknown FUR file: {only}")

    missing = [name for name in selected if not (TEMPLATES_DIR / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing official templates: {', '.join(missing)}")

    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    reports: list[dict[str, Any]] = []
    try:
        for filename in selected:
            source = TEMPLATES_DIR / filename
            target = _output_path(source)
            _convert_to_docx(word, source, target)
            protection_removed = _remove_docx_protection(target)
            report = _add_controls(word, target, _fur_number(filename))
            report["protection_removed"] = protection_removed
            reports.append(report)
    finally:
        word.Quit()

    manifest = {
        "templates_directory": str(TEMPLATES_DIR),
        "documents": reports,
        "total_controls": sum(item["content_controls"] for item in reports),
        "total_failures": sum(len(item["failures"]) for item in reports),
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Process one source filename, e.g. fur5_ci_p.doc")
    args = parser.parse_args()
    manifest = generate(args.only)
    for document in manifest["documents"]:
        print(
            f"{document['output']}: "
            f"{document['content_controls']}/{document['legacy_form_fields']} controls, "
            f"{len(document['failures'])} failures"
        )
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
