"""Rehidrata archivos legacy locales desde Google Drive (jobs completed).

La carga masiva dejó filas en `folders` + `student_drive_sync_jobs.drive_file_id`,
pero el binario a veces no está en el FILES_DIR del servidor (404 al descargar).

Uso (en el servidor de producción, o con FILES_DIR apuntando al disco real):
  set DATABASE_URL=...
  python scripts/repair_legacy_local_from_drive.py --dry-run
  python scripts/repair_legacy_local_from_drive.py --apply
  python scripts/repair_legacy_local_from_drive.py --apply --document-id 27
  python scripts/repair_legacy_local_from_drive.py --apply --limit 20
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend.classes.student_drive_sync_class import StudentDriveSyncClass, student_files_dir
from app.backend.db.database import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Escribe archivos faltantes")
    parser.add_argument("--dry-run", action="store_true", help="Solo reporta (default)")
    parser.add_argument("--document-id", type=int, default=None, help="Filtrar doc (7 o 27)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--student-id", type=int, default=None)
    args = parser.parse_args()
    apply = bool(args.apply) and not bool(args.dry_run)

    out_dir = student_files_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"FILES_DIR students = {out_dir}")

    db = SessionLocal()
    sync = StudentDriveSyncClass(db)
    try:
        sql = """
            SELECT f.id AS folder_id, f.student_id, f.document_id, f.file,
                   j.drive_file_id, j.drive_path
            FROM folders f
            INNER JOIN student_drive_sync_jobs j
              ON j.folder_id = f.id
             AND j.status = 'completed'
             AND j.drive_file_id IS NOT NULL
            WHERE f.deleted_date IS NULL
              AND f.file IS NOT NULL
              AND TRIM(f.file) <> ''
              AND f.file LIKE '%legacy%'
        """
        params: dict = {}
        if args.document_id is not None:
            sql += " AND f.document_id = :document_id"
            params["document_id"] = int(args.document_id)
        if args.student_id is not None:
            sql += " AND f.student_id = :student_id"
            params["student_id"] = int(args.student_id)
        sql += " ORDER BY f.id ASC"
        if args.limit is not None:
            sql += " LIMIT :lim"
            params["lim"] = int(args.limit)

        rows = db.execute(text(sql), params).mappings().all()
        counts = {"ok": 0, "skip": 0, "error": 0, "missing_local": 0}
        for row in rows:
            filename = Path(str(row["file"])).name
            target = out_dir / filename
            if target.is_file() and target.stat().st_size > 0:
                counts["skip"] += 1
                continue
            counts["missing_local"] += 1
            folder_id = int(row["folder_id"])
            print(
                f"missing folder={folder_id} student={row['student_id']} "
                f"doc={row['document_id']} file={filename} drive={row['drive_file_id']}"
            )
            if not apply:
                continue
            try:
                payload = sync.download_for_folder(folder_id)
                data = payload["data"]
                target.write_bytes(data)
                print(f"  wrote {target} ({len(data)} bytes)")
                counts["ok"] += 1
            except Exception as exc:
                counts["error"] += 1
                print(f"  ERROR: {exc}")
        print("done", counts, "apply" if apply else "dry-run")
    finally:
        db.close()


if __name__ == "__main__":
    main()
