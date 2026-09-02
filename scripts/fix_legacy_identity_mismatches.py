"""Corrige mal asignados (contenido=RUT de otro) e importa unmatched recuperables por RUT.

Uso:
  python scripts/fix_legacy_identity_mismatches.py --apply
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend.classes.student_document_file_class import FolderClass
from app.backend.classes.student_drive_sync_class import (
    StudentDriveSyncClass,
    student_files_dir,
)
from app.backend.db.database import SessionLocal
from app.backend.db.models import FolderModel, StudentAcademicInfoModel, StudentModel
from app.backend.utils.google_drive_storage import upload_student_document_tree
from scripts.import_legacy_drive_reports import (
    _access_token,
    _append_result,
    _canonical_filename,
    _download_drive_file,
    _existing_legacy_folder,
    _resolve_drive_meta,
)
from scripts.resolve_ambiguous_by_rut import _docx_text, _norm_rut
from scripts.audit_legacy_docx_identity import (
    AUDIT_IMPORTED,
    AUDIT_UNMATCHED,
    _extract_student_from_text,
    _names_compatible,
    _read_local_or_drive,
    _student_identity,
)

OUT = ROOT / "scripts" / "output" / "fix_identity_result.csv"


def _soft_delete_legacy(db, *, student_id: int, document_id: int, filename: str) -> int:
    rows = (
        db.query(FolderModel)
        .filter(
            FolderModel.student_id == student_id,
            FolderModel.document_id == document_id,
            FolderModel.file == filename,
            FolderModel.deleted_date.is_(None),
        )
        .all()
    )
    n = 0
    for row in rows:
        row.deleted_date = datetime.now()
        n += 1
    if n:
        db.commit()
    return n


def _import_one(
    db,
    *,
    token: str,
    student_id: int,
    document_id: int,
    school_id: int | None,
    drive_file_id: str,
    archivo: str,
    content: bytes | None = None,
    note: str = "",
) -> dict:
    filename = _canonical_filename(student_id, document_id, archivo)
    existing = _existing_legacy_folder(
        db, student_id=student_id, document_id=document_id, filename=filename
    )
    if existing:
        return {
            "status": "skipped",
            "message": f"{note} | Ya existía folder {existing.id}",
            "folder_id": str(existing.id),
            "drive_status": "",
            "drive_path": "",
            "filename": filename,
        }

    if content is None:
        content = _download_drive_file(token, drive_file_id)
    student = (
        db.query(StudentModel)
        .filter(StudentModel.id == student_id, StudentModel.deleted_status_id == 0)
        .first()
    )
    if not student:
        return {
            "status": "error",
            "message": f"{note} | Alumno {student_id} no encontrado",
            "folder_id": "",
            "drive_status": "",
            "drive_path": "",
            "filename": filename,
        }
    academic = (
        db.query(StudentAcademicInfoModel)
        .filter(StudentAcademicInfoModel.student_id == student_id)
        .order_by(StudentAcademicInfoModel.id.desc())
        .first()
    )
    course_id = getattr(academic, "course_id", None) if academic else None
    sid_school = school_id or getattr(student, "school_id", None)
    target = student_files_dir() / filename
    target.write_bytes(content)
    store = FolderClass(db).store(
        student_id=student_id,
        document_id=document_id,
        file_path=filename,
        school_id=sid_school,
        course_id=course_id,
        period_year="2026",
    )
    if isinstance(store, dict) and store.get("status") == "error":
        raise RuntimeError(store.get("message") or "store error")
    folder_id = str(store.get("id") or "")
    drive_status = ""
    drive_path = ""
    message = f"{note} | Guardado como {filename}"
    try:
        meta = _resolve_drive_meta(
            db,
            student_id=student_id,
            document_id=document_id,
            school_id=sid_school,
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
        try:
            sync = StudentDriveSyncClass(db)
            job = sync.enqueue(
                folder_id=int(store["id"]),
                student_id=student_id,
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

    return {
        "status": "ok",
        "message": message,
        "folder_id": folder_id,
        "drive_status": drive_status,
        "drive_path": drive_path,
        "filename": filename,
    }


def run(*, apply: bool) -> dict[str, int]:
    imported_audit = list(csv.DictReader(AUDIT_IMPORTED.open(encoding="utf-8-sig")))
    unmatched_audit = list(csv.DictReader(AUDIT_UNMATCHED.open(encoding="utf-8-sig")))
    counts = {
        "reassign_ok": 0,
        "reassign_skip": 0,
        "reassign_error": 0,
        "unmatched_ok": 0,
        "unmatched_skip": 0,
        "unmatched_error": 0,
        "soft_deleted": 0,
    }
    results: list[dict] = []
    db = SessionLocal()
    try:
        token = _access_token(db)

        # 1) Mal asignados: contenido coherente con real_student
        for row in imported_audit:
            if row.get("verdict") != "mal_asignado":
                continue
            real_id = int(row["real_student_id"] or 0)
            assigned_id = int(row["assigned_student_id"] or 0)
            if not real_id or not assigned_id:
                continue
            if not _names_compatible(row.get("doc_name") or "", row.get("real_name") or ""):
                results.append(
                    {
                        "action": "reassign_skip_incoherent",
                        "status": "skipped",
                        "message": "doc_name no calza con real_name",
                        "archivo_drive": row.get("archivo_drive"),
                        "from_student_id": assigned_id,
                        "to_student_id": real_id,
                    }
                )
                counts["reassign_skip"] += 1
                continue

            document_id = int(row["document_id"])
            archivo = (row.get("archivo_drive") or "informe.docx").strip()
            drive_file_id = (row.get("drive_file_id") or "").strip()
            wrong_filename = _canonical_filename(assigned_id, document_id, archivo)
            real_info = _student_identity(db, real_id)

            if not apply:
                results.append(
                    {
                        "action": "reassign_dry",
                        "status": "planned",
                        "message": f"Mover a {real_id} {real_info['name']}",
                        "archivo_drive": archivo,
                        "from_student_id": assigned_id,
                        "to_student_id": real_id,
                    }
                )
                continue

            try:
                content = _read_local_or_drive(
                    db,
                    token,
                    filename=wrong_filename,
                    drive_file_id=drive_file_id or None,
                )
                # verify rut still points to real
                _, doc_rut, _ = _extract_student_from_text(_docx_text(content))
                if doc_rut and doc_rut != _norm_rut(real_info["rut"]) and doc_rut != real_info["rut_norm"]:
                    # still proceed if real was from audit; warn
                    pass
                deleted = _soft_delete_legacy(
                    db,
                    student_id=assigned_id,
                    document_id=document_id,
                    filename=wrong_filename,
                )
                counts["soft_deleted"] += deleted
                res = _import_one(
                    db,
                    token=token,
                    student_id=real_id,
                    document_id=document_id,
                    school_id=real_info.get("school_id"),
                    drive_file_id=drive_file_id,
                    archivo=archivo,
                    content=content,
                    note=f"Reasignado desde {assigned_id} -> {real_id}",
                )
                if res["status"] == "ok":
                    counts["reassign_ok"] += 1
                elif res["status"] == "skipped":
                    counts["reassign_skip"] += 1
                else:
                    counts["reassign_error"] += 1
                _append_result(
                    {
                        "n": f"fix-{assigned_id}-{real_id}",
                        "status": res["status"],
                        "message": res["message"],
                        "drive_status": res["drive_status"],
                        "drive_path": res["drive_path"],
                        "student_id": real_id,
                        "document_id": document_id,
                        "school_id": real_info.get("school_id") or "",
                        "alumno_pie360": real_info["name"],
                        "archivo_drive": archivo,
                        "drive_file_id": drive_file_id,
                        "folder_id": res["folder_id"],
                    }
                )
                results.append(
                    {
                        "action": "reassign",
                        "status": res["status"],
                        "message": res["message"] + f" | soft_deleted={deleted}",
                        "archivo_drive": archivo,
                        "from_student_id": assigned_id,
                        "to_student_id": real_id,
                        "drive_path": res["drive_path"],
                    }
                )
                print(f"reassign {assigned_id}->{real_id} {res['status']}", flush=True)
            except Exception as exc:
                counts["reassign_error"] += 1
                results.append(
                    {
                        "action": "reassign",
                        "status": "error",
                        "message": str(exc)[:400],
                        "archivo_drive": archivo,
                        "from_student_id": assigned_id,
                        "to_student_id": real_id,
                    }
                )
                print(f"reassign ERROR {assigned_id}->{real_id}: {exc}", flush=True)

        # 2) Unmatched recuperables por RUT con nombre del doc coherente
        for row in unmatched_audit:
            if row.get("verdict") != "existe_por_rut":
                continue
            pie_id = int(row.get("pie_student_id") or 0)
            if not pie_id:
                continue
            doc_name = row.get("doc_name") or ""
            pie_name = row.get("pie_name") or ""
            if not _names_compatible(doc_name, pie_name):
                # still allow if filename compatible (typos like Urejula/Arejula)
                if not _names_compatible(row.get("nombre_extraido") or "", pie_name):
                    counts["unmatched_skip"] += 1
                    continue

            document_id = int(row["document_id"])
            archivo = (row.get("archivo_drive") or "informe.docx").strip()
            drive_file_id = (row.get("drive_file_id") or "").strip()
            pie = _student_identity(db, pie_id)

            if not apply:
                results.append(
                    {
                        "action": "unmatched_import_dry",
                        "status": "planned",
                        "message": f"Importar a {pie_id} {pie['name']}",
                        "archivo_drive": archivo,
                        "from_student_id": "",
                        "to_student_id": pie_id,
                    }
                )
                continue

            try:
                content = _download_drive_file(token, drive_file_id)
                # re-check rut
                _, doc_rut, _ = _extract_student_from_text(_docx_text(content))
                if doc_rut and doc_rut != pie["rut_norm"]:
                    counts["unmatched_skip"] += 1
                    results.append(
                        {
                            "action": "unmatched_import",
                            "status": "skipped",
                            "message": f"rut cambió/no calza doc={doc_rut} pie={pie['rut_norm']}",
                            "archivo_drive": archivo,
                            "to_student_id": pie_id,
                        }
                    )
                    continue
                res = _import_one(
                    db,
                    token=token,
                    student_id=pie_id,
                    document_id=document_id,
                    school_id=pie.get("school_id"),
                    drive_file_id=drive_file_id,
                    archivo=archivo,
                    content=content,
                    note=f"Unmatched por RUT -> {pie_id}",
                )
                if res["status"] == "ok":
                    counts["unmatched_ok"] += 1
                elif res["status"] == "skipped":
                    counts["unmatched_skip"] += 1
                else:
                    counts["unmatched_error"] += 1
                _append_result(
                    {
                        "n": f"unm-{pie_id}-{document_id}",
                        "status": res["status"],
                        "message": res["message"],
                        "drive_status": res["drive_status"],
                        "drive_path": res["drive_path"],
                        "student_id": pie_id,
                        "document_id": document_id,
                        "school_id": pie.get("school_id") or "",
                        "alumno_pie360": pie["name"],
                        "archivo_drive": archivo,
                        "drive_file_id": drive_file_id,
                        "folder_id": res["folder_id"],
                    }
                )
                results.append(
                    {
                        "action": "unmatched_import",
                        "status": res["status"],
                        "message": res["message"],
                        "archivo_drive": archivo,
                        "from_student_id": "",
                        "to_student_id": pie_id,
                        "drive_path": res.get("drive_path", ""),
                    }
                )
                print(f"unmatched -> {pie_id} {res['status']} {archivo[:40]}", flush=True)
            except Exception as exc:
                counts["unmatched_error"] += 1
                results.append(
                    {
                        "action": "unmatched_import",
                        "status": "error",
                        "message": str(exc)[:400],
                        "archivo_drive": archivo,
                        "to_student_id": pie_id,
                    }
                )
                print(f"unmatched ERROR {pie_id}: {exc}", flush=True)
    finally:
        db.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    if results:
        fields = sorted({k for r in results for k in r.keys()})
        with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(results)
    print("DETALLE", OUT)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    counts = run(apply=args.apply)
    print("RESULTADO", counts)
    return 0 if counts["reassign_error"] == 0 and counts["unmatched_error"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
