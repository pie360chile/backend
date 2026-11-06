"""Borra anamnesis/folders/sync jobs/local PDF del intento de import Drive."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DATABASE_URL"] = (
    os.environ.get("IMPORT_DATABASE_URL")
    or "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.backend.classes.anamnesis_class import ANAMNESIS_DOCUMENT_ID
from app.backend.db.models import AnamnesisModel, FolderModel

os.environ["DATABASE_URL"] = (
    os.environ.get("IMPORT_DATABASE_URL")
    or "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
)

LOCAL_STUDENT_FILES = ROOT / "files" / "system" / "students"


def main() -> None:
    eng = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=eng)()

    folders = (
        db.query(FolderModel)
        .filter(
            FolderModel.document_id == ANAMNESIS_DOCUMENT_ID,
            FolderModel.file.like("%anamnesis_drive.pdf"),
        )
        .all()
    )
    folder_ids = [int(f.id) for f in folders]
    detail_ids = sorted({int(f.detail_id) for f in folders if f.detail_id})
    print(f"folders={len(folders)} detail_ids={detail_ids}")

    for fid in folder_ids:
        db.execute(
            text("DELETE FROM student_drive_sync_jobs WHERE folder_id = :fid"),
            {"fid": fid},
        )

    for f in folders:
        path = LOCAL_STUDENT_FILES / (f.file or "")
        if path.is_file():
            path.unlink(missing_ok=True)
        db.delete(f)

    if detail_ids:
        rows = (
            db.query(AnamnesisModel)
            .filter(AnamnesisModel.id.in_(detail_ids))
            .all()
        )
    else:
        rows = []
    print(f"anamnesis_rows={len(rows)} ids={[r.id for r in rows]}")
    for r in rows:
        for table in (
            "anamnesis_informants",
            "anamnesis_interviewers",
            "anamnesis_household_members",
        ):
            try:
                db.execute(
                    text(f"DELETE FROM {table} WHERE anamnesis_id = :aid"),
                    {"aid": int(r.id)},
                )
            except Exception:
                pass
        db.delete(r)

    db.commit()
    print("purge ok")
    db.close()


if __name__ == "__main__":
    main()
