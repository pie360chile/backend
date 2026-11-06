"""Import masivo anamnesis Drive: seed ficha + PDF Drive + DeepSeek visión completa.

Lee matches de scripts/output/anamnesis_dry_run.csv
Progreso: scripts/output/anamnesis_mass_progress.jsonl

Uso:
  python scripts/_tmp_mass_import_anamnesis.py
  python scripts/_tmp_mass_import_anamnesis.py --limit 5
  python scripts/_tmp_mass_import_anamnesis.py --skip-done
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TUNNEL = "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"

from dotenv import load_dotenv

# Primero .env (DEEPSEEK_API_KEY); luego forzar túnel (el .env pisa DATABASE_URL a remoto)
load_dotenv(ROOT / ".env", override=True)
os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL
os.environ["IMPORT_DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL

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
    _resolve_drive_meta,
    _seed_payload_from_student,
    _student_display_name,
    _student_files_dir,
    _truncate_payload_strings,
)
from scripts._tmp_deepseek_full_pdf import (
    PAGE_PROMPTS,
    _call_vision,
    _merge,
    _page_images,
    _sanitize,
    _extract_json,
)
from app.backend.classes.agents_usage_class import AgentsUsageClass
from app.backend.utils.agents_llm_client import DEFAULT_MODEL_CODE, resolve_llm_api_key

os.environ["DATABASE_URL"] = TUNNEL


def _api_key(db) -> str:
    key = (resolve_llm_api_key(db) or "").strip()
    if key:
        return key
    key = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    if key:
        return key
    raise RuntimeError("Sin DEEPSEEK_API_KEY")

DRY_CSV = ROOT / "scripts" / "output" / "anamnesis_dry_run.csv"
PROGRESS = ROOT / "scripts" / "output" / "anamnesis_mass_progress.jsonl"
PDF_CACHE = ROOT / "scripts" / "output" / "anamnesis_pdfs"
CUSTOMER_ID = 2


def _done_ids() -> set[int]:
    out: set[int] = set()
    if not PROGRESS.exists():
        return out
    for line in PROGRESS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("status") == "ok" and row.get("student_id"):
            out.add(int(row["student_id"]))
    return out


def _log(row: dict) -> None:
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    with PROGRESS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()


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


def _fresh_db():
    os.environ["DATABASE_URL"] = TUNNEL
    eng = create_engine(TUNNEL, pool_pre_ping=True)
    return eng, sessionmaker(bind=eng)()


def _deepseek_update(db, pdf_path: Path, anamnesis_id: int, student_id: int, api_key: str) -> dict:
    import fitz

    doc = fitz.open(pdf_path)
    n_pages = len(doc)
    doc.close()
    model = DEFAULT_MODEL_CODE
    merged: dict = {}
    total_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "prompt_cache_hit_tokens": 0,
        "prompt_cache_miss_tokens": 0,
    }
    for i in range(n_pages):
        prompt = PAGE_PROMPTS.get(i, PAGE_PROMPTS[min(4, max(PAGE_PROMPTS))])
        images = _page_images(pdf_path, i)
        text, usage = _call_vision(api_key, model, prompt, images)
        parsed = _extract_json(text)
        merged = _merge(merged, parsed)
        if usage:
            for k in total_usage:
                total_usage[k] += int(usage.get(k) or 0)
        try:
            AgentsUsageClass(db).record_chat(
                customer_id=CUSTOMER_ID,
                school_id=None,
                user_id=None,
                agent_id="anamnesis_import_ocr",
                model=model,
                prompt_tokens=int((usage or {}).get("prompt_tokens") or 0),
                completion_tokens=int((usage or {}).get("completion_tokens") or 0),
                total_tokens=int((usage or {}).get("total_tokens") or 0),
                prompt_cache_hit_tokens=int((usage or {}).get("prompt_cache_hit_tokens") or 0),
                prompt_cache_miss_tokens=int((usage or {}).get("prompt_cache_miss_tokens") or 0),
                input_text=f"anamnesis full-pdf student={student_id} page={i+1}/{n_pages}",
                output_text=(text or "")[:5000],
                request_kind="anamnesis_ocr",
            )
        except Exception as e:
            print(f"  WARN usage: {e}", flush=True)
            db.rollback()

    merged = _sanitize(merged)
    cls = AnamnesisClass(db)
    cur = cls.get(anamnesis_id) or {}
    upd = {k: v for k, v in merged.items() if v not in (None, "", [])}
    for keep in ("gender_id", "nationality_id"):
        upd.pop(keep, None)
    # identidad preferir ficha si ya hay valor
    for keep in ("student_full_name", "born_date", "address", "phone", "school_name", "current_schooling", "current_level"):
        if cur.get(keep) and keep in upd:
            # name/level del PDF puede ser peor; conservar ficha salvo current_level corto del form
            if keep != "current_level":
                upd[keep] = cur[keep]
    for k in ("informants", "interviewers", "household_members"):
        if k not in upd and cur.get(k):
            upd[k] = cur[k]
    res = cls.update(anamnesis_id, upd)
    return {"update": res, "fields": len(upd), "usage": total_usage, "pages": n_pages}


def process_one(row: dict, *, purge: bool) -> dict:
    student_id = int(row["student_id"])
    drive_file_id = row["drive_file_id"]
    name = (row.get("sample_student_full_name") or row.get("nombre_archivo") or f"id={student_id}").strip()
    t0 = time.time()
    eng, db = _fresh_db()
    try:
        if not name or name.startswith("id="):
            name = _student_display_name(db, student_id) or name
        print(f">>> INICIA: {name} (student_id={student_id})", flush=True)

        if purge:
            _purge(db, student_id)

        PDF_CACHE.mkdir(parents=True, exist_ok=True)
        pdf_path = PDF_CACHE / f"{student_id}_{drive_file_id}.pdf"
        if pdf_path.exists() and pdf_path.stat().st_size > 1000:
            content = pdf_path.read_bytes()
            print(f"  PDF cache {pdf_path.name} ({len(content)} bytes)", flush=True)
        else:
            token = _access_token(db)
            content = _download_drive_file(token, drive_file_id)
            pdf_path.write_bytes(content)
            print(f"  PDF descargado ({len(content)} bytes)", flush=True)

        seed = _seed_payload_from_student(db, student_id)
        payload = _truncate_payload_strings(seed)
        payload["final_comments"] = (
            "Importado desde PDF escaneado ANAMNESIS (DeepSeek visión). Revisar manuscritos."
        )
        store = AnamnesisClass(db).store(payload)
        if isinstance(store, dict) and store.get("status") == "error":
            raise RuntimeError(store.get("message") or "store error")
        anamnesis_id = int(store["id"])
        version = store.get("version")
        print(f"  anamnesis id={anamnesis_id} v={version}", flush=True)

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
            raise RuntimeError(folder_store.get("message") or "folder error")
        folder_id = int(folder_store.get("id") if isinstance(folder_store, dict) else folder_store)
        rowf = db.query(FolderModel).filter(FolderModel.id == folder_id).first()
        if rowf:
            rowf.detail_id = anamnesis_id
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
        print(f"  Drive OK {drive_payload.get('drive_path')}", flush=True)

        api_key = _api_key(db)
        print("  DeepSeek visión (todas las páginas)...", flush=True)
        ds = _deepseek_update(db, pdf_path, anamnesis_id, student_id, api_key)
        print(f"  DeepSeek fields={ds['fields']} pages={ds['pages']} tokens={ds['usage'].get('total_tokens')}", flush=True)

        elapsed = round(time.time() - t0, 1)
        print(f"LISTO: {name}", flush=True)
        out = {
            "status": "ok",
            "student_id": student_id,
            "name": name,
            "anamnesis_id": anamnesis_id,
            "version": version,
            "folder_id": folder_id,
            "drive_path": drive_payload.get("drive_path"),
            "deepseek_fields": ds["fields"],
            "elapsed_s": elapsed,
            "archivo": row.get("archivo"),
        }
        _log(out)
        return out
    except Exception as e:
        elapsed = round(time.time() - t0, 1)
        err = {
            "status": "error",
            "student_id": student_id,
            "name": name,
            "error": str(e),
            "elapsed_s": elapsed,
            "archivo": row.get("archivo"),
            "trace": traceback.format_exc()[-1500:],
        }
        print(f"ERROR: {name} -> {e}", flush=True)
        _log(err)
        try:
            db.rollback()
        except Exception:
            pass
        return err
    finally:
        try:
            db.close()
        except Exception:
            pass
        try:
            eng.dispose()
        except Exception:
            pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--skip-done", action="store_true", default=True)
    ap.add_argument("--no-skip-done", action="store_true")
    ap.add_argument("--skip-student-id", type=int, action="append", default=[])
    ap.add_argument("--only-student-id", type=int, action="append", default=[])
    ap.add_argument("--no-purge", action="store_true")
    args = ap.parse_args()
    skip_done = False if args.no_skip_done else True

    if not DRY_CSV.exists():
        raise SystemExit(f"Falta {DRY_CSV}: corre dry-run primero")

    rows = list(csv.DictReader(DRY_CSV.open(encoding="utf-8")))
    matched = [r for r in rows if r.get("status") == "ok" and r.get("student_id")]
    # dedupe por student_id (quedarse con el primero)
    seen: set[int] = set()
    unique = []
    for r in matched:
        sid = int(r["student_id"])
        if sid in seen:
            continue
        seen.add(sid)
        unique.append(r)

    done = _done_ids() if skip_done else set()
    skip_ids = set(args.skip_student_id or [])
    # Dafnika ya hecha a mano con buena calidad
    skip_ids.add(1851)

    queue = []
    for r in unique:
        sid = int(r["student_id"])
        if args.only_student_id and sid not in set(args.only_student_id):
            continue
        if sid in skip_ids:
            continue
        if sid in done:
            continue
        queue.append(r)

    if args.limit:
        queue = queue[: args.limit]

    print(
        f"matched_unique={len(unique)} done={len(done)} queue={len(queue)} skip={skip_ids}",
        flush=True,
    )
    ok = err = 0
    for i, r in enumerate(queue, 1):
        print(f"\n===== [{i}/{len(queue)}] =====", flush=True)
        res = process_one(r, purge=not args.no_purge)
        if res.get("status") == "ok":
            ok += 1
        else:
            err += 1
    print(f"\n===== FIN ok={ok} err={err} restantes_previos_done={len(done)} =====", flush=True)


if __name__ == "__main__":
    main()
