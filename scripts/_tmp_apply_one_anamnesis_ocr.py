"""Aplica anamnesis OCR (EasyOCR+RapidOCR) a UN alumno: formulario + PDF + Drive.

Uso:
  python scripts/_tmp_apply_one_anamnesis_ocr.py --student-id 1851 --drive-file-id 1KVU...
  python scripts/_tmp_apply_one_anamnesis_ocr.py --student-id 1851 --pdf path/al.pdf
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TUNNEL = "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL

import numpy as np
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

os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL


def _purge(db, student_id: int) -> None:
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
            p = _student_files_dir() / f.file
            if p.is_file():
                p.unlink(missing_ok=True)
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
    print(f"purged folders={len(folders)} anamnesis={len(rows)}", flush=True)


def _pdf_images(content: bytes, *, zoom: float = 2.0, max_pages: int = 8):
    import cv2
    import fitz

    images = []
    doc = fitz.open(stream=content, filetype="pdf")
    try:
        mat = fitz.Matrix(zoom, zoom)
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(matrix=mat, alpha=False)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            images.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    finally:
        doc.close()
    return images


def _ocr_easy(images) -> str:
    import easyocr

    reader = easyocr.Reader(["es", "en"], gpu=False, verbose=False)
    parts = []
    for img in images:
        result = reader.readtext(img, detail=0, paragraph=True)
        page = "\n".join(str(x).strip() for x in result if str(x).strip())
        if page:
            parts.append(page)
    return "\n\n".join(parts)


def _ocr_rapid(images) -> str:
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR()
    parts = []
    for img in images:
        result, _ = engine(img)
        if not result:
            continue
        lines = [str(item[1]).strip() for item in result if item and len(item) > 1]
        page = "\n".join(ln for ln in lines if ln)
        if page:
            parts.append(page)
    return "\n\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--student-id", type=int, required=True)
    ap.add_argument("--drive-file-id", default="")
    ap.add_argument("--pdf", default="")
    ap.add_argument("--reuse-ocr-dir", default="")
    ap.add_argument("--no-purge", action="store_true")
    args = ap.parse_args()

    os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL
    eng = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=eng)()
    student_id = int(args.student_id)

    if not args.no_purge:
        _purge(db, student_id)

    content: bytes
    if args.pdf and Path(args.pdf).is_file():
        content = Path(args.pdf).read_bytes()
        print(f"PDF local {args.pdf} ({len(content)} bytes)", flush=True)
    elif args.drive_file_id:
        token = _access_token(db)
        content = _download_drive_file(token, args.drive_file_id)
        print(f"PDF Drive {args.drive_file_id} ({len(content)} bytes)", flush=True)
    else:
        raise SystemExit("Indica --pdf o --drive-file-id")

    ocr_dir = Path(args.reuse_ocr_dir) if args.reuse_ocr_dir else None
    easy_txt = rapid_txt = ""
    if ocr_dir and ocr_dir.exists():
        ep = ocr_dir / "easyocr_text.txt"
        rp = ocr_dir / "rapidocr_text.txt"
        if ep.exists():
            easy_txt = ep.read_text(encoding="utf-8")
        if rp.exists():
            rapid_txt = rp.read_text(encoding="utf-8")
        print(f"Reusando OCR dir {ocr_dir}", flush=True)

    if not easy_txt or not rapid_txt:
        print("Render + OCR EasyOCR/RapidOCR...", flush=True)
        images = _pdf_images(content)
        if not easy_txt:
            easy_txt = _ocr_easy(images)
        if not rapid_txt:
            rapid_txt = _ocr_rapid(images)

    seed = _seed_payload_from_student(db, student_id)
    extracted: dict = {"_mapped_keys": []}
    name_fb = _student_display_name(db, student_id)
    for label, txt in (("easy", easy_txt), ("rapid", rapid_txt)):
        if not txt:
            continue
        part = map_pdf_to_anamnesis_payload(
            student_id=student_id, text=txt, fields={}, student_name_fallback=name_fb
        )
        print(f"{label} mapped={len(part.get('_mapped_keys') or [])}", flush=True)
        extracted = _merge_payloads(extracted, part)

    payload = _merge_payloads(seed, extracted)
    mapped = payload.pop("_mapped_keys", []) or []
    payload = _truncate_payload_strings(payload)
    print(f"TOTAL mapped={len(mapped)}", flush=True)

    store = AnamnesisClass(db).store(payload)
    if isinstance(store, dict) and store.get("status") == "error":
        raise RuntimeError(store.get("message"))
    anamnesis_id = int(store["id"])
    version = store.get("version")
    print(f"anamnesis id={anamnesis_id} v={version}", flush=True)

    meta = _resolve_drive_meta(db, student_id=student_id, period_year="2026")
    pdf_filename = f"{student_id}_{ANAMNESIS_DOCUMENT_ID}_anamnesis_drive.pdf"
    target = _student_files_dir() / pdf_filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)

    folder_store = FolderClass(db).store(
        student_id=student_id,
        document_id=ANAMNESIS_DOCUMENT_ID,
        file_path=pdf_filename,
        school_id=meta["school_id"],
        course_id=meta.get("course_id"),
        period_year="2026",
    )
    if isinstance(folder_store, dict) and folder_store.get("status") == "error":
        raise RuntimeError(folder_store.get("message"))
    folder_id = int(folder_store.get("id") if isinstance(folder_store, dict) else folder_store)
    row = db.query(FolderModel).filter(FolderModel.id == folder_id).first()
    if row:
        row.detail_id = anamnesis_id
        db.commit()

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
        student_id=student_id,
        document_id=ANAMNESIS_DOCUMENT_ID,
        file_path=f"system/students/{pdf_filename}",
        mime_type="application/pdf",
    )
    job.status = "completed"
    job.drive_file_id = drive_payload.get("file_id")
    job.drive_path = drive_payload.get("drive_path")
    job.last_error = None
    db.commit()

    data = AnamnesisClass(db).get(anamnesis_id) or {}
    filled = {
        k: v
        for k, v in data.items()
        if v not in (None, "", [], {}) and k not in {"status", "message"}
    }
    print("===== OK =====", flush=True)
    print(f"student_id={student_id} anamnesis_id={anamnesis_id} v={version}", flush=True)
    print(f"folder_id={folder_id}", flush=True)
    print(f"drive_path={drive_payload.get('drive_path')}", flush=True)
    print(f"campos_con_valor={len(filled)} mapped_keys={len(mapped)}", flush=True)
    hh = data.get("household_members") or []
    print(f"household={len(hh)}", flush=True)
    for m in hh:
        print(f"  - {m}", flush=True)
    db.close()


if __name__ == "__main__":
    main()
