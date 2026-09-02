"""Importa a PIE360 los informes legacy de Drive con match único y los sincroniza
al árbol nuevo Liceo/Año/Curso/RUT/RUT_TipoDocumento.ext.

Uso:
  python scripts/import_legacy_drive_reports.py --apply
  python scripts/import_legacy_drive_reports.py --apply --limit 5
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import requests
from sqlalchemy.exc import OperationalError

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
    CourseModel,
    DocumentModel,
    FolderModel,
    SchoolModel,
    StudentAcademicInfoModel,
    StudentModel,
    StudentPersonalInfoModel,
)
from app.backend.utils.customer_drive_config import load_customer_drive_config
from app.backend.utils.google_drive_storage import upload_student_document_tree


OK_CSV = ROOT / "scripts" / "output" / "import_ok.csv"
RESULT_CSV = ROOT / "scripts" / "output" / "import_apply_result.csv"
RESULT_FIELDS = [
    "n",
    "status",
    "message",
    "drive_status",
    "drive_path",
    "student_id",
    "document_id",
    "school_id",
    "alumno_pie360",
    "archivo_drive",
    "drive_file_id",
    "folder_id",
]


def _new_db():
    return SessionLocal()


def _reconnect(db, *, reason: str = ""):
    try:
        db.close()
    except Exception:
        pass
    print(f"reconectando MySQL... {reason}", flush=True)
    time.sleep(3)
    return _new_db()


def _access_token(db) -> str:
    cfg = load_customer_drive_config(db, 2)
    oauth = cfg.oauth_info or {}
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": oauth["client_id"],
            "client_secret": oauth["client_secret"],
            "refresh_token": oauth["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _download_drive_file(access_token: str, file_id: str) -> bytes:
    response = requests.get(
        f"https://www.googleapis.com/drive/v3/files/{file_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"alt": "media"},
        timeout=120,
    )
    response.raise_for_status()
    return response.content


def _canonical_filename(student_id: int, document_id: int, source_name: str) -> str:
    ext = Path(source_name).suffix.lower() or ".docx"
    if ext not in {".docx", ".pdf", ".doc"}:
        ext = ".docx"
    return f"{student_id}_{document_id}_legacy_2026{ext}"


def _load_ok_rows() -> list[dict]:
    if not OK_CSV.is_file():
        raise FileNotFoundError(f"No existe {OK_CSV}. Genera primero el CSV de matches.")
    with OK_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _resolve_drive_meta(db, *, student_id: int, document_id: int, school_id: int | None, course_id: int | None, period_year: str = "2026") -> dict:
    student = db.query(StudentModel).filter(StudentModel.id == student_id).first()
    if not student:
        raise ValueError("Alumno no encontrado para metadata Drive")
    personal = (
        db.query(StudentPersonalInfoModel)
        .filter(StudentPersonalInfoModel.student_id == student_id)
        .order_by(StudentPersonalInfoModel.id.desc())
        .first()
    )
    school = (
        db.query(SchoolModel)
        .filter(SchoolModel.id == int(school_id or student.school_id or 0))
        .first()
    )
    if not school or not school.customer_id:
        raise ValueError("No se pudo resolver liceo/cliente")
    course = None
    if course_id:
        course = db.query(CourseModel).filter(CourseModel.id == int(course_id)).first()
    document = db.query(DocumentModel).filter(DocumentModel.id == int(document_id)).first()
    rut = (getattr(personal, "identification_number", None) if personal else None) or student.identification_number
    if not rut:
        raise ValueError("El alumno no tiene RUT")
    return {
        "customer_id": int(school.customer_id),
        "school_name": school.school_name or f"Liceo {school.id}",
        "year": int(period_year),
        "course_name": (course.course_name if course else None) or "Curso",
        "student_rut": str(rut),
        "document_type_name": (document.document if document else None) or f"Documento {document_id}",
    }


def _existing_legacy_folder(db, *, student_id: int, document_id: int, filename: str):
    return (
        db.query(FolderModel)
        .filter(
            FolderModel.student_id == student_id,
            FolderModel.document_id == document_id,
            FolderModel.file == filename,
            FolderModel.deleted_date.is_(None),
        )
        .order_by(FolderModel.id.desc())
        .first()
    )


def _append_result(row: dict) -> None:
    RESULT_CSV.parent.mkdir(parents=True, exist_ok=True)
    write_header = not RESULT_CSV.is_file() or RESULT_CSV.stat().st_size == 0
    with RESULT_CSV.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def apply_import(*, limit: int | None = None) -> dict[str, int]:
    rows = _load_ok_rows()
    if limit is not None:
        rows = rows[: max(0, int(limit))]

    # Reanudación: no sobrescribir resultados previos; se append-ean.
    RESULT_CSV.parent.mkdir(parents=True, exist_ok=True)

    db = _new_db()
    counts = {"ok": 0, "error": 0, "skipped": 0, "drive_ok": 0, "drive_pending": 0}
    try:
        token = _access_token(db)
        upload_dir = student_files_dir()
        for index, row in enumerate(rows, start=1):
            student_id = int(row["student_id"])
            document_id = int(row["document_id"])
            school_id = int(row["school_id"])
            drive_file_id = (row.get("drive_file_id") or "").strip()
            archivo = (row.get("archivo_drive") or "informe.docx").strip()
            filename = _canonical_filename(student_id, document_id, archivo)
            status = "error"
            message = ""
            folder_id = ""
            drive_path = ""
            drive_status = ""
            attempts = 0
            while attempts < 3:
                attempts += 1
                try:
                    existing = _existing_legacy_folder(
                        db,
                        student_id=student_id,
                        document_id=document_id,
                        filename=filename,
                    )
                    if existing:
                        counts["skipped"] += 1
                        status = "skipped"
                        folder_id = str(existing.id)
                        message = f"Ya existía {filename} (folder {existing.id})"
                        break

                    student = (
                        db.query(StudentModel)
                        .filter(
                            StudentModel.id == student_id,
                            StudentModel.deleted_status_id == 0,
                        )
                        .first()
                    )
                    if not student:
                        counts["skipped"] += 1
                        status = "skipped"
                        message = "Alumno no encontrado"
                        break

                    academic = (
                        db.query(StudentAcademicInfoModel)
                        .filter(StudentAcademicInfoModel.student_id == student_id)
                        .order_by(StudentAcademicInfoModel.id.desc())
                        .first()
                    )
                    course_id = getattr(academic, "course_id", None) if academic else None
                    content = _download_drive_file(token, drive_file_id)
                    if not content:
                        raise ValueError("Archivo vacío en Drive")
                    target = upload_dir / filename
                    target.write_bytes(content)
                    store = FolderClass(db).store(
                        student_id=student_id,
                        document_id=document_id,
                        file_path=filename,
                        school_id=school_id or getattr(student, "school_id", None),
                        course_id=course_id,
                        period_year="2026",
                    )
                    if isinstance(store, dict) and store.get("status") == "error":
                        raise RuntimeError(store.get("message") or "Error guardando folders")
                    folder_id = str(store.get("id") or "")
                    status = "ok"
                    message = f"Guardado como {filename}"
                    counts["ok"] += 1

                    # Subir de inmediato al árbol nuevo de Drive.
                    try:
                        meta = _resolve_drive_meta(
                            db,
                            student_id=student_id,
                            document_id=document_id,
                            school_id=school_id or getattr(student, "school_id", None),
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
                            try:
                                db.rollback()
                            except Exception:
                                db = _reconnect(db, reason="rollback sync")
                    except Exception as drive_exc:
                        drive_status = "pending"
                        counts["drive_pending"] += 1
                        message += f" | Drive pendiente: {drive_exc}"
                        try:
                            StudentDriveSyncClass(db).enqueue(
                                folder_id=int(store["id"]),
                                student_id=student_id,
                                document_id=document_id,
                                file_path=f"system/students/{filename}",
                            )
                        except Exception:
                            try:
                                db.rollback()
                            except Exception:
                                db = _reconnect(db, reason="rollback enqueue")
                    break
                except OperationalError as exc:
                    message = str(exc)[:500]
                    try:
                        db.rollback()
                    except Exception:
                        pass
                    db = _reconnect(db, reason=str(exc)[:120])
                    try:
                        token = _access_token(db)
                    except Exception:
                        pass
                    if attempts >= 3:
                        counts["error"] += 1
                        status = "error"
                except Exception as exc:
                    try:
                        db.rollback()
                    except Exception:
                        db = _reconnect(db, reason="rollback genérico")
                    if status != "ok":
                        counts["error"] += 1
                        status = "error"
                        message = str(exc)[:500]
                    else:
                        message += f" | post-error: {exc}"
                    if "401" in str(exc) or "invalid_grant" in str(exc).lower():
                        try:
                            token = _access_token(db)
                        except Exception:
                            pass
                    break

            result_row = {
                "n": index,
                "status": status,
                "message": message,
                "drive_status": drive_status,
                "drive_path": drive_path,
                "student_id": student_id,
                "document_id": document_id,
                "school_id": school_id,
                "alumno_pie360": row.get("alumno_pie360", ""),
                "archivo_drive": archivo,
                "drive_file_id": drive_file_id,
                "folder_id": folder_id,
            }
            _append_result(result_row)
            if index % 25 == 0 or status == "error":
                print(
                    f"progreso {index}/{len(rows)} "
                    f"ok={counts['ok']} skipped={counts['skipped']} "
                    f"drive_ok={counts['drive_ok']} "
                    f"drive_pending={counts['drive_pending']} err={counts['error']}",
                    flush=True,
                )
    finally:
        try:
            db.close()
        except Exception:
            pass

    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa informes legacy Drive -> PIE360 + árbol nuevo")
    parser.add_argument("--apply", action="store_true", help="Descarga e importa matches únicos")
    parser.add_argument("--limit", type=int, default=None, help="Limitar cantidad (prueba)")
    args = parser.parse_args()
    if not args.apply:
        print("Usa --apply para importar. Los CSV de revisión están en scripts/output/")
        return 0
    counts = apply_import(limit=args.limit)
    print("RESULTADO", counts)
    print("DETALLE", RESULT_CSV)
    return 0 if counts["error"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
