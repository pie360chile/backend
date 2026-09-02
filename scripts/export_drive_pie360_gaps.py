"""Genera 2 CSV de brechas Drive vs PIE360: Informe Familia (7) e Informe Psicopedagógico (27).

- Archivos/alumnos en Drive sin alumno en PIE360 → aparecen en ambos con '(No estan en pie360)'
- Tiene Familia y falta Psico → sale en CSV Psico
- Tiene Psico y falta Familia → sale en CSV Familia

Uso:
  python scripts/export_drive_pie360_gaps.py
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend.db.database import SessionLocal

OUT = ROOT / "scripts" / "output"
OK = OUT / "import_ok.csv"
UNMATCHED = OUT / "import_unmatched.csv"
AMBIGUOUS = OUT / "import_ambiguous.csv"
APPLY = OUT / "import_apply_result.csv"
FIX = OUT / "fix_identity_result.csv"
AUDIT_UNM = OUT / "audit_unmatched_identity.csv"
RESOLVED_AMB = OUT / "import_ambiguous_resolved.csv"

CSV_FAMILIA = OUT / "brechas_informe_familia.csv"
CSV_PSICO = OUT / "brechas_informe_psicopedagogico.csv"

DOC_FAMILIA = 7
DOC_PSICO = 27
LABEL = {DOC_FAMILIA: "Informe a la Familia", DOC_PSICO: "Informe Psicopedagógico"}


def _read(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _name(names, father, mother) -> str:
    return " ".join(p for p in [names or "", father or "", mother or ""] if p).strip().upper()


def _load_drive_inventory() -> dict[str, dict]:
    """drive_file_id -> metadata from ok/unmatched/ambiguous."""
    inv: dict[str, dict] = {}
    for path, source in ((OK, "ok"), (UNMATCHED, "unmatched"), (AMBIGUOUS, "ambiguous")):
        for row in _read(path):
            fid = (row.get("drive_file_id") or "").strip()
            if not fid:
                continue
            inv[fid] = {
                "drive_file_id": fid,
                "document_id": int(row.get("document_id") or 0),
                "tipo_informe": row.get("tipo_informe") or LABEL.get(int(row.get("document_id") or 0), ""),
                "school_id": row.get("school_id") or "",
                "liceo": row.get("liceo") or "",
                "archivo_drive": row.get("archivo_drive") or "",
                "nombre_extraido": row.get("nombre_extraido") or "",
                "link_drive": row.get("link_drive") or "",
                "source_match": source,
                "student_id_match": row.get("student_id") or "",
                "alumno_match": row.get("alumno_pie360") or "",
            }
    return inv


def _successful_drive_to_student() -> dict[str, int]:
    """drive_file_id -> student_id for imports that ended ok/skipped with student."""
    mapping: dict[str, int] = {}
    for row in _read(APPLY):
        status = (row.get("status") or "").lower()
        fid = (row.get("drive_file_id") or "").strip()
        sid = (row.get("student_id") or "").strip()
        if fid and sid and status in {"ok", "skipped"}:
            mapping[fid] = int(sid)
    # ambiguous resolved / ethan-to-simon etc already in APPLY via append
    for row in _read(RESOLVED_AMB):
        status = (row.get("status") or "").lower()
        fid = (row.get("drive_file_id") or "").strip()
        sid = (row.get("student_id") or "").strip()
        if fid and sid and status in {"ok", "skipped", "resolved"}:
            # only if later applied; resolved alone without apply shouldn't count
            if status in {"ok", "skipped"}:
                mapping[fid] = int(sid)
    # fix reassign/unmatched: APPLY appends those too; also FIX for to_student
    for row in _read(FIX):
        status = (row.get("status") or "").lower()
        if status != "ok":
            continue
        # FIX csv may not have drive_file_id; recover from APPLY messages already handled
        to_sid = (row.get("to_student_id") or "").strip()
        archivo = (row.get("archivo_drive") or "").strip()
        if not to_sid or not archivo:
            continue
        # map via inventory archivo
        # filled below after inventory known — skip here
    return mapping


def _pie360_docs(db) -> dict[int, set[int]]:
    """student_id -> set of document_ids present (active folders 7/27 2026)."""
    school_ids = [
        int(r[0])
        for r in db.execute(text("SELECT id FROM schools WHERE customer_id = 2")).fetchall()
    ]
    if not school_ids:
        return {}
    placeholders = ",".join(str(int(s)) for s in school_ids)
    rows = db.execute(
        text(
            f"""
            SELECT f.student_id, f.document_id
            FROM folders f
            JOIN students s ON s.id = f.student_id AND s.deleted_status_id = 0
            WHERE f.deleted_date IS NULL
              AND f.document_id IN (7, 27)
              AND (
                f.period_year = '2026'
                OR f.file LIKE '%legacy_2026%'
              )
              AND (f.school_id IN ({placeholders}) OR s.school_id IN ({placeholders}))
            """
        )
    ).fetchall()
    out: dict[int, set[int]] = defaultdict(set)
    for sid, doc_id in rows:
        out[int(sid)].add(int(doc_id))
    return out


def _student_meta(db, student_ids: set[int]) -> dict[int, dict]:
    if not student_ids:
        return {}
    ids = ",".join(str(int(i)) for i in student_ids)
    rows = db.execute(
        text(
            f"""
            SELECT s.id, s.school_id, s.identification_number,
                   p.names, p.father_lastname, p.mother_lastname, p.identification_number
            FROM students s
            LEFT JOIN student_personal_data p ON p.student_id = s.id
              AND p.id = (
                SELECT MAX(p2.id) FROM student_personal_data p2 WHERE p2.student_id = s.id
              )
            WHERE s.id IN ({ids})
            """
        )
    ).fetchall()
    meta: dict[int, dict] = {}
    for sid, school_id, s_rut, names, father, mother, p_rut in rows:
        meta[int(sid)] = {
            "student_id": int(sid),
            "school_id": school_id,
            "rut": p_rut or s_rut or "",
            "alumno_pie360": _name(names, father, mother),
        }
    return meta


def _school_names(db) -> dict[int, str]:
    rows = db.execute(text("SELECT id, school_name FROM schools WHERE customer_id = 2")).fetchall()
    return {int(r[0]): (r[1] or "") for r in rows}


def main() -> int:
    inv = _load_drive_inventory()
    drive_to_student = _successful_drive_to_student()

    # Enrich mapping from APPLY by archivo for FIX ok rows without fid
    archivo_to_fid = {
        (v["archivo_drive"] or "").strip(): fid for fid, v in inv.items() if v.get("archivo_drive")
    }
    for row in _read(FIX):
        if (row.get("status") or "").lower() != "ok":
            continue
        to_sid = (row.get("to_student_id") or "").strip()
        archivo = (row.get("archivo_drive") or "").strip()
        fid = archivo_to_fid.get(archivo)
        if to_sid and fid:
            drive_to_student[fid] = int(to_sid)

    # Unmatched audit: if existe_por_rut and later imported, already in APPLY;
    # remaining without pie stay as not in pie360
    db = SessionLocal()
    try:
        pie_docs = _pie360_docs(db)
        school_names = _school_names(db)
        all_sids = set(pie_docs.keys()) | set(drive_to_student.values())
        meta = _student_meta(db, all_sids)
    finally:
        db.close()

    # Students known from Drive content (successful import)
    students_with_drive_familia: set[int] = set()
    students_with_drive_psico: set[int] = set()
    for fid, sid in drive_to_student.items():
        item = inv.get(fid)
        if not item:
            continue
        if item["document_id"] == DOC_FAMILIA:
            students_with_drive_familia.add(sid)
        elif item["document_id"] == DOC_PSICO:
            students_with_drive_psico.add(sid)

    # Also count PIE360 folders as "tiene"
    students_familia = {sid for sid, docs in pie_docs.items() if DOC_FAMILIA in docs} | students_with_drive_familia
    students_psico = {sid for sid, docs in pie_docs.items() if DOC_PSICO in docs} | students_with_drive_psico

    familia_rows: list[dict] = []
    psico_rows: list[dict] = []

    # 1) Drive files not linked to PIE360 student (or linked student missing that doc after soft-delete)
    not_in_pie_fids: list[str] = []
    for fid, item in inv.items():
        sid = drive_to_student.get(fid)
        if sid is None:
            not_in_pie_fids.append(fid)
            continue
        # if assigned but that doc not present in pie folders (e.g. soft-deleted and not reimported)
        docs = pie_docs.get(sid, set())
        if item["document_id"] not in docs:
            # still count as gap for that document type if not in folders
            not_in_pie_fids.append(fid)

    # Deduplicate: for true "no en pie360" only when no student mapping
    for fid, item in inv.items():
        sid = drive_to_student.get(fid)
        doc_id = item["document_id"]
        base = {
            "tipo_informe": LABEL[doc_id] if doc_id in LABEL else item.get("tipo_informe"),
            "document_id": doc_id,
            "school_id": item.get("school_id") or "",
            "liceo": item.get("liceo") or "",
            "archivo_drive": item.get("archivo_drive") or "",
            "nombre_en_drive": item.get("nombre_extraido") or "",
            "drive_file_id": fid,
            "link_drive": item.get("link_drive") or "",
            "student_id": "",
            "alumno_pie360": "",
            "rut": "",
            "tiene_familia_pie360": "no",
            "tiene_psico_pie360": "no",
        }
        if sid is None:
            row = {
                **base,
                "motivo": "(No estan en pie360)",
                "detalle": "Archivo en Drive sin alumno asociado en PIE360",
            }
            # Sale en AMBOS CSV
            familia_rows.append({**row, "csv": "familia"})
            psico_rows.append({**row, "csv": "psico"})
            continue

        # Linked to student: check cross gaps below; if doc missing from folders, gap in that CSV only
        info = meta.get(sid, {})
        has_f = "si" if sid in students_familia else "no"
        has_p = "si" if sid in students_psico else "no"
        if doc_id == DOC_FAMILIA and sid not in students_familia:
            familia_rows.append(
                {
                    **base,
                    "student_id": sid,
                    "alumno_pie360": info.get("alumno_pie360") or "",
                    "rut": info.get("rut") or "",
                    "school_id": info.get("school_id") or base["school_id"],
                    "liceo": school_names.get(int(info["school_id"]), base["liceo"])
                    if info.get("school_id")
                    else base["liceo"],
                    "tiene_familia_pie360": has_f,
                    "tiene_psico_pie360": has_p,
                    "motivo": "Drive familia sin carpeta activa en PIE360",
                    "detalle": f"Había match a student_id={sid} pero no hay folder activo doc 7",
                }
            )
        if doc_id == DOC_PSICO and sid not in students_psico:
            psico_rows.append(
                {
                    **base,
                    "student_id": sid,
                    "alumno_pie360": info.get("alumno_pie360") or "",
                    "rut": info.get("rut") or "",
                    "school_id": info.get("school_id") or base["school_id"],
                    "liceo": school_names.get(int(info["school_id"]), base["liceo"])
                    if info.get("school_id")
                    else base["liceo"],
                    "tiene_familia_pie360": has_f,
                    "tiene_psico_pie360": has_p,
                    "motivo": "Drive psico sin carpeta activa en PIE360",
                    "detalle": f"Había match a student_id={sid} pero no hay folder activo doc 27",
                }
            )

    # 2) Cruces: tiene uno, falta el otro (alumnos PIE360)
    missing_meta = (students_psico | students_familia) - set(meta.keys())
    if missing_meta:
        db2 = SessionLocal()
        try:
            meta.update(_student_meta(db2, missing_meta))
        finally:
            db2.close()

    for sid in sorted(students_psico - students_familia):
        info = meta.get(sid, {})
        familia_rows.append(
            {
                "tipo_informe": LABEL[DOC_FAMILIA],
                "document_id": DOC_FAMILIA,
                "school_id": info.get("school_id") or "",
                "liceo": school_names.get(int(info["school_id"]), "") if info.get("school_id") else "",
                "archivo_drive": "",
                "nombre_en_drive": "",
                "drive_file_id": "",
                "link_drive": "",
                "student_id": sid,
                "alumno_pie360": info.get("alumno_pie360") or "",
                "rut": info.get("rut") or "",
                "tiene_familia_pie360": "no",
                "tiene_psico_pie360": "si",
                "motivo": "Tiene Informe Psicopedagógico, falta Informe a la Familia",
                "detalle": "Alumno en PIE360 con doc 27 y sin doc 7 (2026/legacy)",
            }
        )

    for sid in sorted(students_familia - students_psico):
        info = meta.get(sid, {})
        psico_rows.append(
            {
                "tipo_informe": LABEL[DOC_PSICO],
                "document_id": DOC_PSICO,
                "school_id": info.get("school_id") or "",
                "liceo": school_names.get(int(info["school_id"]), "") if info.get("school_id") else "",
                "archivo_drive": "",
                "nombre_en_drive": "",
                "drive_file_id": "",
                "link_drive": "",
                "student_id": sid,
                "alumno_pie360": info.get("alumno_pie360") or "",
                "rut": info.get("rut") or "",
                "tiene_familia_pie360": "si",
                "tiene_psico_pie360": "no",
                "motivo": "Tiene Informe a la Familia, falta Informe Psicopedagógico",
                "detalle": "Alumno en PIE360 con doc 7 y sin doc 27 (2026/legacy)",
            }
        )

    fields = [
        "motivo",
        "detalle",
        "tipo_informe",
        "document_id",
        "student_id",
        "alumno_pie360",
        "rut",
        "school_id",
        "liceo",
        "tiene_familia_pie360",
        "tiene_psico_pie360",
        "archivo_drive",
        "nombre_en_drive",
        "drive_file_id",
        "link_drive",
    ]

    def _write(path: Path, rows: list[dict]) -> None:
        # drop helper key
        clean = []
        for r in rows:
            clean.append({k: r.get(k, "") for k in fields})
        # de-dupe by (motivo, student_id, drive_file_id, archivo)
        seen = set()
        uniq = []
        for r in clean:
            key = (r["motivo"], str(r["student_id"]), r["drive_file_id"], r["archivo_drive"])
            if key in seen:
                continue
            seen.add(key)
            uniq.append(r)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(uniq)
        print(path.resolve(), "filas=", len(uniq))

    _write(CSV_FAMILIA, familia_rows)
    _write(CSV_PSICO, psico_rows)

    n_both = sum(1 for r in familia_rows if r.get("motivo") == "(No estan en pie360)")
    print(
        "resumen:",
        f"no_en_pie360_ambos≈{n_both}",
        f"familia_csv={CSV_FAMILIA.name}",
        f"psico_csv={CSV_PSICO.name}",
        f"tienen_familia={len(students_familia)}",
        f"tienen_psico={len(students_psico)}",
        f"falta_familia={len(students_psico - students_familia)}",
        f"falta_psico={len(students_familia - students_psico)}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
