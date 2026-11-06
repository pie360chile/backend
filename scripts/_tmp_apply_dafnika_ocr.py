"""Piloto Dafnika: OCR EasyOCR+RapidOCR → formulario anamnesis + PDF local + Drive."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_TUNNEL_DB_URL = "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or DEFAULT_TUNNEL_DB_URL

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.backend.classes.anamnesis_class import ANAMNESIS_DOCUMENT_ID, AnamnesisClass
from app.backend.classes.student_document_file_class import FolderClass
from app.backend.classes.student_drive_sync_class import StudentDriveSyncClass
from app.backend.db.models import AnamnesisModel, FolderModel
from app.backend.utils.google_drive_storage import upload_student_document_tree
from scripts.import_drive_anamnesis import (
    _access_token,
    _download_drive_file,
    _merge_payloads,
    _resolve_drive_meta,
    _seed_payload_from_student,
    _student_display_name,
    _student_files_dir,
    _truncate_payload_strings,
    map_pdf_to_anamnesis_payload,
)

STUDENT_ID = 1851
DRIVE_FILE_ID = "1KVUTB9W91Z3IfB7G_24RTTnc3V5X3miR"
OCR_DIR = ROOT / "scripts" / "output" / "ocr_dafnika"
PDF_PATH = OCR_DIR / "dafnika.pdf"


def _purge_student(db, student_id: int) -> None:
    folders = (
        db.query(FolderModel)
        .filter(
            FolderModel.student_id == student_id,
            FolderModel.document_id == ANAMNESIS_DOCUMENT_ID,
        )
        .all()
    )
    for f in folders:
        try:
            db.execute(
                text("DELETE FROM student_drive_sync_jobs WHERE folder_id = :fid"),
                {"fid": int(f.id)},
            )
        except Exception:
            pass
        if f.file:
            path = _student_files_dir() / f.file
            if path.is_file():
                path.unlink(missing_ok=True)
        db.delete(f)

    rows = db.query(AnamnesisModel).filter(AnamnesisModel.student_id == student_id).all()
    for r in rows:
        for table in (
            "anamnesis_informants",
            "anamnesis_interviewers",
            "anamnesis_household_members",
        ):
            try:
                db.execute(text(f"DELETE FROM {table} WHERE anamnesis_id = :aid"), {"aid": int(r.id)})
            except Exception:
                pass
        db.delete(r)
    db.commit()
    print(f"purged student={student_id} folders={len(folders)} anamnesis={len(rows)}", flush=True)


def _map_from_text(db, text: str) -> dict:
    return map_pdf_to_anamnesis_payload(
        student_id=STUDENT_ID,
        text=text,
        fields={},
        student_name_fallback=_student_display_name(db, STUDENT_ID),
    )


def main() -> None:
    os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or DEFAULT_TUNNEL_DB_URL
    eng = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=eng)()

    _purge_student(db, STUDENT_ID)

    if PDF_PATH.exists() and PDF_PATH.stat().st_size > 1000:
        content = PDF_PATH.read_bytes()
        print(f"PDF local {PDF_PATH} ({len(content)} bytes)", flush=True)
    else:
        print("Descargando PDF desde Drive...", flush=True)
        token = _access_token(db)
        content = _download_drive_file(token, DRIVE_FILE_ID)
        OCR_DIR.mkdir(parents=True, exist_ok=True)
        PDF_PATH.write_bytes(content)

    # Usar los OCR que más mapearon: EasyOCR + RapidOCR (unión)
    easy_txt = (OCR_DIR / "easyocr_text.txt").read_text(encoding="utf-8") if (OCR_DIR / "easyocr_text.txt").exists() else ""
    rapid_txt = (OCR_DIR / "rapidocr_text.txt").read_text(encoding="utf-8") if (OCR_DIR / "rapidocr_text.txt").exists() else ""
    if not easy_txt and not rapid_txt:
        raise RuntimeError("No hay textos OCR previos; corre primero _tmp_ocr_dafnika_compare.py")

    seed = _seed_payload_from_student(db, STUDENT_ID)
    extracted: dict = {"_mapped_keys": []}
    if easy_txt:
        e = _map_from_text(db, easy_txt)
        print(f"EasyOCR mapped={len(e.get('_mapped_keys') or [])}", flush=True)
        extracted = _merge_payloads(extracted, e)
    if rapid_txt:
        r = _map_from_text(db, rapid_txt)
        print(f"RapidOCR mapped={len(r.get('_mapped_keys') or [])}", flush=True)
        extracted = _merge_payloads(extracted, r)

    payload = _merge_payloads(seed, extracted)
    mapped_keys = payload.pop("_mapped_keys", []) or []
    payload = _truncate_payload_strings(payload)
    print(f"TOTAL campos mapeados (unión+seed)={len(mapped_keys)}", flush=True)

    store = AnamnesisClass(db).store(payload)
    if isinstance(store, dict) and store.get("status") == "error":
        raise RuntimeError(store.get("message") or "store failed")
    anamnesis_id = int(store["id"])
    version = store.get("version")
    print(f"anamnesis id={anamnesis_id} version={version}", flush=True)

    meta = _resolve_drive_meta(db, student_id=STUDENT_ID, period_year="2026")
    # San Felipe: forzar nombre de colegio conocido si hace falta
    if not meta.get("school_name"):
        meta["school_name"] = "Liceo Mixto San Felipe"

    pdf_filename = f"{STUDENT_ID}_{ANAMNESIS_DOCUMENT_ID}_anamnesis_drive.pdf"
    target = _student_files_dir() / pdf_filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)

    folder_store = FolderClass(db).store(
        student_id=STUDENT_ID,
        document_id=ANAMNESIS_DOCUMENT_ID,
        file_path=pdf_filename,
        school_id=meta["school_id"],
        course_id=meta.get("course_id"),
        period_year="2026",
    )
    if isinstance(folder_store, dict) and folder_store.get("status") == "error":
        raise RuntimeError(folder_store.get("message") or "folder store failed")
    folder_id = int(folder_store.get("id") if isinstance(folder_store, dict) else folder_store)
    folder_row = db.query(FolderModel).filter(FolderModel.id == folder_id).first()
    if folder_row:
        folder_row.detail_id = anamnesis_id
        db.commit()
    print(f"folder_id={folder_id} file={pdf_filename}", flush=True)

    drive_payload = upload_student_document_tree(
        db=db,
        customer_id=meta["customer_id"],
        school_name=meta["school_name"],
        year=meta["year"],
        course_name=meta["course_name"],
        student_rut=meta["student_rut"],
        document_type_name=meta["document_type_name"],
        data=content,
        file_extension="pdf",
        mime_type="application/pdf",
    )
    sync = StudentDriveSyncClass(db)
    job = sync.enqueue(
        folder_id=folder_id,
        student_id=STUDENT_ID,
        document_id=ANAMNESIS_DOCUMENT_ID,
        file_path=f"system/students/{pdf_filename}",
        mime_type="application/pdf",
    )
    job.status = "completed"
    job.drive_file_id = drive_payload.get("file_id")
    job.drive_path = drive_payload.get("drive_path")
    job.last_error = None
    db.commit()

    data = AnamnesisClass(db).get(anamnesis_id)
    filled = {
        k: v
        for k, v in (data or {}).items()
        if v not in (None, "", [], {}) and k not in {"status", "message"}
    }
    print("===== OK =====", flush=True)
    print(f"student_id={STUDENT_ID}", flush=True)
    print(f"anamnesis_id={anamnesis_id} version={version}", flush=True)
    print(f"folder_id={folder_id}", flush=True)
    print(f"drive_path={drive_payload.get('drive_path')}", flush=True)
    print(f"drive_file_id={drive_payload.get('file_id')}", flush=True)
    print(f"campos_en_formulario={len(filled)}", flush=True)
    print(f"mapped_keys={len(mapped_keys)}", flush=True)
    for k in sorted(filled)[:40]:
        print(f"  {k}={filled[k]!r}"[:180], flush=True)
    db.close()


if __name__ == "__main__":
    main()
