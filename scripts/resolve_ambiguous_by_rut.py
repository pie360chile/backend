"""Resuelve matches ambiguos abriendo el .docx, extrayendo RUT y eligiendo el alumno PIE360.

Uso:
  python scripts/resolve_ambiguous_by_rut.py
  python scripts/resolve_ambiguous_by_rut.py --apply
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend.classes.student_document_file_class import FolderClass
from app.backend.classes.student_drive_sync_class import (
    StudentDriveSyncClass,
    student_files_dir,
)
from app.backend.db.database import SessionLocal
from app.backend.db.models import (
    FolderModel,
    StudentAcademicInfoModel,
    StudentModel,
    StudentPersonalInfoModel,
)
from scripts.import_legacy_drive_reports import (
    RESULT_CSV,
    _access_token,
    _append_result,
    _canonical_filename,
    _download_drive_file,
    _resolve_drive_meta,
)
from app.backend.utils.google_drive_storage import upload_student_document_tree

AMB_CSV = ROOT / "scripts" / "output" / "import_ambiguous.csv"
RESOLVE_CSV = ROOT / "scripts" / "output" / "import_ambiguous_resolved.csv"

RUT_RE = re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b|\b\d{7,8}-[\dkK]\b")


def _norm_rut(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^0-9kK]", "", str(value)).upper()


def _docx_text(content: bytes) -> str:
    texts: list[str] = []
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for name in zf.namelist():
            if name.startswith("word/") and name.endswith(".xml"):
                root = ET.fromstring(zf.read(name))
                for node in root.iter():
                    if node.tag.endswith("}t") and node.text:
                        texts.append(node.text)
                    if node.tail:
                        texts.append(node.tail)
    return " ".join(texts)


def _extract_ruts(text: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for match in RUT_RE.finditer(text or ""):
        norm = _norm_rut(match.group(0))
        if norm and norm not in seen:
            seen.add(norm)
            ordered.append(norm)
    return ordered


def _parse_candidate_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for part in (raw or "").split(";"):
        part = part.strip()
        if not part:
            continue
        sid = part.split("|", 1)[0].strip()
        if sid.isdigit():
            ids.append(int(sid))
    return ids


def _student_display_name(db, student_id: int) -> str:
    personal = (
        db.query(StudentPersonalInfoModel)
        .filter(StudentPersonalInfoModel.student_id == student_id)
        .order_by(StudentPersonalInfoModel.id.desc())
        .first()
    )
    if not personal:
        return ""
    parts = [
        personal.names or "",
        personal.father_lastname or "",
        personal.mother_lastname or "",
    ]
    return " ".join(str(p).strip() for p in parts if p).strip().upper()


def _rut_for_student(db, student_id: int) -> str:
    personal = (
        db.query(StudentPersonalInfoModel)
        .filter(StudentPersonalInfoModel.student_id == student_id)
        .order_by(StudentPersonalInfoModel.id.desc())
        .first()
    )
    if personal and personal.identification_number:
        return _norm_rut(personal.identification_number)
    student = db.query(StudentModel).filter(StudentModel.id == student_id).first()
    return _norm_rut(getattr(student, "identification_number", None) if student else None)


def _resolve_student(db, *, candidate_ids: list[int], doc_ruts: list[str]) -> tuple[int | None, str]:
    if not doc_ruts:
        return None, "sin_rut_en_documento"
    rut_set = set(doc_ruts)
    matched: list[int] = []
    for sid in candidate_ids:
        if _rut_for_student(db, sid) in rut_set:
            matched.append(sid)
    if len(matched) == 1:
        return matched[0], f"rut_unico_en_candidatos:{doc_ruts[0] if len(doc_ruts)==1 else ','.join(doc_ruts[:3])}"
    if len(matched) > 1:
        return None, f"varios_candidatos_con_rut:{matched}"
    # Si ningún candidato coincide, buscar en el colegio de los candidatos no aplica aquí;
    # preferimos no adivinar fuera de la lista ambigua.
    return None, f"rut_no_coincide_candidatos:{','.join(doc_ruts[:5])}"


def resolve_rows(*, apply: bool = False) -> dict[str, int]:
    rows = list(csv.DictReader(AMB_CSV.open(encoding="utf-8-sig")))
    db = SessionLocal()
    out_rows: list[dict] = []
    counts = {"resolved": 0, "unresolved": 0, "ok": 0, "skipped": 0, "error": 0, "drive_ok": 0}
    try:
        token = _access_token(db)
        upload_dir = student_files_dir()
        for index, row in enumerate(rows, start=1):
            document_id = int(row["document_id"])
            school_id = int(row["school_id"])
            drive_file_id = (row.get("drive_file_id") or "").strip()
            archivo = (row.get("archivo_drive") or "informe.docx").strip()
            candidate_ids = _parse_candidate_ids(row.get("candidatos") or "")
            status = "unresolved"
            message = ""
            student_id = ""
            alumno = ""
            folder_id = ""
            drive_status = ""
            drive_path = ""
            try:
                content = _download_drive_file(token, drive_file_id)
                text = _docx_text(content)
                doc_ruts = _extract_ruts(text)
                sid, reason = _resolve_student(db, candidate_ids=candidate_ids, doc_ruts=doc_ruts)
                message = reason
                if sid is None:
                    counts["unresolved"] += 1
                else:
                    student_id = str(sid)
                    alumno = _student_display_name(db, sid)
                    counts["resolved"] += 1
                    status = "resolved"
                    if apply:
                        filename = _canonical_filename(sid, document_id, archivo)
                        existing = (
                            db.query(FolderModel)
                            .filter(
                                FolderModel.student_id == sid,
                                FolderModel.document_id == document_id,
                                FolderModel.file == filename,
                                FolderModel.deleted_date.is_(None),
                            )
                            .order_by(FolderModel.id.desc())
                            .first()
                        )
                        if existing:
                            counts["skipped"] += 1
                            status = "skipped"
                            folder_id = str(existing.id)
                            message = f"{reason} | Ya existía folder {existing.id}"
                        else:
                            academic = (
                                db.query(StudentAcademicInfoModel)
                                .filter(StudentAcademicInfoModel.student_id == sid)
                                .order_by(StudentAcademicInfoModel.id.desc())
                                .first()
                            )
                            course_id = getattr(academic, "course_id", None) if academic else None
                            target = upload_dir / filename
                            target.write_bytes(content)
                            store = FolderClass(db).store(
                                student_id=sid,
                                document_id=document_id,
                                file_path=filename,
                                school_id=school_id,
                                course_id=course_id,
                                period_year="2026",
                            )
                            if isinstance(store, dict) and store.get("status") == "error":
                                raise RuntimeError(store.get("message") or "Error folders")
                            folder_id = str(store.get("id") or "")
                            status = "ok"
                            counts["ok"] += 1
                            message = f"{reason} | Guardado como {filename}"
                            try:
                                meta = _resolve_drive_meta(
                                    db,
                                    student_id=sid,
                                    document_id=document_id,
                                    school_id=school_id,
                                    course_id=course_id,
                                    period_year="2026",
                                )
                                payload = upload_student_document_tree(
                                    db=db,
                                    customer_id=meta["customer_id"],
                                    school_name=meta["school_name"],
                                    year=meta["year"],
                                    course_name=meta["course_name"],
                                    student_rut=meta["student_rut"],
                                    document_type_name=meta["document_type_name"],
                                    data=content,
                                    file_extension=Path(filename).suffix.lstrip("."),
                                )
                                drive_status = "ok"
                                drive_path = payload.get("drive_path") or ""
                                counts["drive_ok"] += 1
                                try:
                                    sync = StudentDriveSyncClass(db)
                                    job = sync.enqueue(
                                        folder_id=int(store["id"]),
                                        student_id=sid,
                                        document_id=document_id,
                                        file_path=f"system/students/{filename}",
                                    )
                                    job.status = "completed"
                                    job.drive_file_id = payload.get("file_id")
                                    job.drive_path = drive_path
                                    job.last_error = None
                                    db.commit()
                                except Exception:
                                    db.rollback()
                            except Exception as drive_exc:
                                drive_status = "pending"
                                message += f" | Drive pendiente: {drive_exc}"
                            _append_result(
                                {
                                    "n": f"amb-{index}",
                                    "status": status,
                                    "message": message,
                                    "drive_status": drive_status,
                                    "drive_path": drive_path,
                                    "student_id": student_id,
                                    "document_id": document_id,
                                    "school_id": school_id,
                                    "alumno_pie360": alumno,
                                    "archivo_drive": archivo,
                                    "drive_file_id": drive_file_id,
                                    "folder_id": folder_id,
                                }
                            )
            except Exception as exc:
                counts["error"] += 1
                status = "error"
                message = str(exc)[:500]
            out_rows.append(
                {
                    "n": index,
                    "status": status,
                    "message": message,
                    "student_id": student_id,
                    "alumno_pie360": alumno,
                    "document_id": document_id,
                    "school_id": school_id,
                    "archivo_drive": archivo,
                    "drive_file_id": drive_file_id,
                    "folder_id": folder_id,
                    "drive_status": drive_status,
                    "drive_path": drive_path,
                    "candidatos": row.get("candidatos", ""),
                }
            )
            print(f"{index}/13 {status} {archivo} -> {alumno or message}", flush=True)
    finally:
        db.close()

    RESOLVE_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = list(out_rows[0].keys()) if out_rows else []
    with RESOLVE_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)
    print("DETALLE", RESOLVE_CSV)
    print("APPLY_LOG", RESULT_CSV)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Importar los que se resuelvan por RUT")
    args = parser.parse_args()
    counts = resolve_rows(apply=args.apply)
    print("RESULTADO", counts)
    return 0 if counts["error"] == 0 and counts["unresolved"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
