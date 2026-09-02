"""Audita informes legacy: RUT/nombre dentro del Word vs alumno del match (o lookup por RUT).

Uso:
  python scripts/audit_legacy_docx_identity.py
"""

from __future__ import annotations

import csv
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend.classes.student_drive_sync_class import student_files_dir
from app.backend.db.database import SessionLocal
from app.backend.db.models import StudentModel, StudentPersonalInfoModel
from scripts.import_legacy_drive_reports import _access_token, _download_drive_file
from scripts.resolve_ambiguous_by_rut import _docx_text, _extract_ruts, _norm_rut

OUT = ROOT / "scripts" / "output"
APPLY = OUT / "import_apply_result.csv"
OK = OUT / "import_ok.csv"
UNMATCHED = OUT / "import_unmatched.csv"
AUDIT_IMPORTED = OUT / "audit_imported_identity.csv"
AUDIT_UNMATCHED = OUT / "audit_unmatched_identity.csv"
AUDIT_SUMMARY = OUT / "audit_identity_summary.txt"

STUDENT_BLOCK_RE = re.compile(
    r"(?:IDENTIFICACI[OÓ]N\s+DEL\s+ESTUDIANTE|CACI[OÓ]N\s+DEL\s+ESTUDIANTE|DEL\s+ESTUDIANTE)\s*"
    r"(?P<name>.{3,80}?)\s+"
    r"(?P<rut>\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]|\d{7,8}-[\dkK])",
    flags=re.I | re.S,
)


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^A-Z0-9 ]", " ", s.upper())
    return re.sub(r"\s+", " ", s).strip()


def _student_identity(db, student_id: int) -> dict:
    personal = (
        db.query(StudentPersonalInfoModel)
        .filter(StudentPersonalInfoModel.student_id == student_id)
        .order_by(StudentPersonalInfoModel.id.desc())
        .first()
    )
    student = db.query(StudentModel).filter(StudentModel.id == student_id).first()
    name = " ".join(
        filter(
            None,
            [
                personal.names if personal else None,
                personal.father_lastname if personal else None,
                personal.mother_lastname if personal else None,
            ],
        )
    )
    rut = (personal.identification_number if personal else None) or (
        student.identification_number if student else None
    )
    return {
        "student_id": student_id,
        "name": name,
        "rut": rut or "",
        "rut_norm": _norm_rut(rut),
        "school_id": getattr(student, "school_id", None),
    }


def _lookup_by_rut(db, rut_norm: str) -> list[dict]:
    if not rut_norm:
        return []
    from sqlalchemy import text

    rows = db.execute(
        text(
            """
            SELECT DISTINCT s.id
            FROM students s
            LEFT JOIN student_personal_data p ON p.student_id = s.id
            WHERE s.deleted_status_id = 0
              AND (
                REPLACE(REPLACE(UPPER(IFNULL(p.identification_number,'')), '.', ''), '-', '') = :rut
                OR REPLACE(REPLACE(UPPER(IFNULL(s.identification_number,'')), '.', ''), '-', '') = :rut
              )
            LIMIT 20
            """
        ),
        {"rut": rut_norm},
    ).fetchall()
    return [_student_identity(db, int(r[0])) for r in rows]


def _extract_student_from_text(text: str) -> tuple[str, str, list[str]]:
    """Return (name_in_doc, rut_norm, all_ruts)."""
    all_ruts = _extract_ruts(text)
    m = STUDENT_BLOCK_RE.search(text or "")
    if m:
        name = re.sub(r"\s+", " ", m.group("name")).strip()
        # clean junk labels accidentally captured
        name = re.sub(r"(Nombre de identidad.*)$", "", name, flags=re.I).strip()
        return name, _norm_rut(m.group("rut")), all_ruts
    if all_ruts:
        return "", all_ruts[0], all_ruts
    return "", "", []


def _names_compatible(a: str, b: str) -> bool:
    fa, fb = _fold(a), _fold(b)
    if not fa or not fb:
        return False
    ta, tb = set(fa.split()), set(fb.split())
    # at least 2 overlapping tokens, or one contains the other
    if len(ta & tb) >= 2:
        return True
    return fa in fb or fb in fa


def _read_local_or_drive(db, token: str | None, *, filename: str | None, drive_file_id: str | None) -> bytes:
    upload_dir = student_files_dir()
    if filename:
        path = upload_dir / filename
        if path.is_file():
            return path.read_bytes()
    if drive_file_id:
        if not token:
            token = _access_token(db)
        return _download_drive_file(token, drive_file_id)
    raise FileNotFoundError("Sin archivo local ni drive_file_id")


def audit_imported(db) -> list[dict]:
    # Prefer apply result (includes ambiguous + simon); fall back to ok
    source = APPLY if APPLY.is_file() else OK
    rows = list(csv.DictReader(source.open(encoding="utf-8-sig")))
    # unique by student_id+document_id+drive_file_id keeping last
    uniq: dict[str, dict] = {}
    for row in rows:
        if (row.get("status") or "") not in {"ok", "skipped"}:
            # still audit skipped/ok only; include amb rows with student_id
            if not row.get("student_id"):
                continue
        key = f"{row.get('student_id')}|{row.get('document_id')}|{row.get('drive_file_id')}"
        uniq[key] = row
    rows = list(uniq.values())
    token = None
    out: list[dict] = []
    for index, row in enumerate(rows, start=1):
        student_id = int(row["student_id"])
        document_id = int(row["document_id"])
        archivo = (row.get("archivo_drive") or "").strip()
        drive_file_id = (row.get("drive_file_id") or "").strip()
        assigned = _student_identity(db, student_id)
        filename = f"{student_id}_{document_id}_legacy_2026{Path(archivo).suffix.lower() or '.docx'}"
        verdict = "error"
        msg = ""
        doc_name = ""
        doc_rut = ""
        real_hits: list[dict] = []
        try:
            content = _read_local_or_drive(
                db, token, filename=filename, drive_file_id=drive_file_id or None
            )
            text = _docx_text(content)
            doc_name, doc_rut, all_ruts = _extract_student_from_text(text)
            if not doc_rut:
                verdict = "sin_rut_en_doc"
                msg = f"ruts={','.join(all_ruts[:5])}"
            elif doc_rut == assigned["rut_norm"]:
                if doc_name and not _names_compatible(doc_name, assigned["name"]):
                    verdict = "rut_ok_nombre_difiere"
                    msg = f"doc='{doc_name}' pie='{assigned['name']}'"
                else:
                    verdict = "ok"
                    msg = "rut coincide"
            else:
                real_hits = _lookup_by_rut(db, doc_rut)
                if len(real_hits) == 1:
                    verdict = "mal_asignado"
                    msg = (
                        f"doc_rut={doc_rut} pertenece a "
                        f"{real_hits[0]['student_id']} {real_hits[0]['name']} "
                        f"(asignado {student_id} {assigned['name']})"
                    )
                elif len(real_hits) > 1:
                    verdict = "rut_doc_multiples"
                    msg = f"doc_rut={doc_rut} hits={[h['student_id'] for h in real_hits]}"
                else:
                    verdict = "rut_doc_no_en_pie360"
                    msg = (
                        f"doc_rut={doc_rut} name_doc='{doc_name}' "
                        f"asignado {student_id} {assigned['name']} rut={assigned['rut_norm']}"
                    )
        except Exception as exc:
            verdict = "error_lectura"
            msg = str(exc)[:300]
            if "401" in msg or "invalid_grant" in msg.lower():
                token = _access_token(db)

        out.append(
            {
                "n": index,
                "verdict": verdict,
                "message": msg,
                "archivo_drive": archivo,
                "drive_file_id": drive_file_id,
                "document_id": document_id,
                "assigned_student_id": student_id,
                "assigned_name": assigned["name"],
                "assigned_rut": assigned["rut"],
                "doc_name": doc_name,
                "doc_rut_norm": doc_rut,
                "real_student_id": real_hits[0]["student_id"] if len(real_hits) == 1 else "",
                "real_name": real_hits[0]["name"] if len(real_hits) == 1 else "",
                "source_status": row.get("status", ""),
            }
        )
        if index % 25 == 0:
            print(f"imported {index}/{len(rows)}", flush=True)
    return out


def audit_unmatched(db) -> list[dict]:
    rows = list(csv.DictReader(UNMATCHED.open(encoding="utf-8-sig")))
    token = _access_token(db)
    out: list[dict] = []
    for index, row in enumerate(rows, start=1):
        archivo = (row.get("archivo_drive") or "").strip()
        drive_file_id = (row.get("drive_file_id") or "").strip()
        school_id = row.get("school_id", "")
        document_id = row.get("document_id", "")
        nombre_extraido = row.get("nombre_extraido", "")
        verdict = "error"
        msg = ""
        doc_name = ""
        doc_rut = ""
        hits: list[dict] = []
        try:
            content = _download_drive_file(token, drive_file_id)
            text = _docx_text(content)
            doc_name, doc_rut, all_ruts = _extract_student_from_text(text)
            if not doc_rut:
                verdict = "sin_rut_en_doc"
                msg = f"ruts={','.join(all_ruts[:5])} nombre_archivo='{nombre_extraido}'"
            else:
                hits = _lookup_by_rut(db, doc_rut)
                if len(hits) == 1:
                    h = hits[0]
                    name_ok = _names_compatible(doc_name or nombre_extraido, h["name"])
                    school_ok = str(h.get("school_id") or "") == str(school_id)
                    if name_ok or school_ok:
                        verdict = "existe_por_rut"
                        msg = f"match {h['student_id']} {h['name']} school={h['school_id']} name_ok={name_ok}"
                    else:
                        verdict = "existe_por_rut_nombre_difiere"
                        msg = (
                            f"match {h['student_id']} {h['name']} "
                            f"doc='{doc_name}' archivo='{nombre_extraido}'"
                        )
                elif len(hits) > 1:
                    verdict = "rut_multiples"
                    msg = f"hits={[ (h['student_id'], h['name']) for h in hits ]}"
                else:
                    verdict = "rut_no_en_pie360"
                    msg = f"doc_rut={doc_rut} doc_name='{doc_name}' archivo='{nombre_extraido}'"
        except Exception as exc:
            verdict = "error_lectura"
            msg = str(exc)[:300]
            if "401" in msg or "invalid_grant" in msg.lower():
                try:
                    token = _access_token(db)
                except Exception:
                    pass

        out.append(
            {
                "n": index,
                "verdict": verdict,
                "message": msg,
                "archivo_drive": archivo,
                "nombre_extraido": nombre_extraido,
                "drive_file_id": drive_file_id,
                "document_id": document_id,
                "school_id": school_id,
                "doc_name": doc_name,
                "doc_rut_norm": doc_rut,
                "pie_student_id": hits[0]["student_id"] if len(hits) == 1 else "",
                "pie_name": hits[0]["name"] if len(hits) == 1 else "",
                "pie_school_id": hits[0]["school_id"] if len(hits) == 1 else "",
            }
        )
        if index % 25 == 0:
            print(f"unmatched {index}/{len(rows)}", flush=True)
    return out


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    db = SessionLocal()
    try:
        print("Auditando importados...", flush=True)
        imported = audit_imported(db)
        _write(AUDIT_IMPORTED, imported)
        print("Auditando unmatched...", flush=True)
        unmatched = audit_unmatched(db)
        _write(AUDIT_UNMATCHED, unmatched)

        from collections import Counter

        c_imp = Counter(r["verdict"] for r in imported)
        c_un = Counter(r["verdict"] for r in unmatched)
        lines = [
            f"imported_total={len(imported)}",
            f"imported_verdicts={dict(c_imp)}",
            f"unmatched_total={len(unmatched)}",
            f"unmatched_verdicts={dict(c_un)}",
            f"imported_csv={AUDIT_IMPORTED}",
            f"unmatched_csv={AUDIT_UNMATCHED}",
        ]
        AUDIT_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines), flush=True)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
