"""Inspecciona el import de prueba (1 estudiante) y verifica Drive."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_TUNNEL_DB_URL = (
    "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
)
os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or DEFAULT_TUNNEL_DB_URL

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.backend.classes.anamnesis_class import ANAMNESIS_DOCUMENT_ID, AnamnesisClass
from app.backend.db.models import AnamnesisModel, FolderModel
from app.backend.utils.customer_drive_config import load_customer_drive_config
from app.backend.utils.google_drive_storage import _service_for_config

os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or DEFAULT_TUNNEL_DB_URL

STUDENT_ID = 5233


def main() -> None:
    eng = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=eng)()

    anams = (
        db.query(AnamnesisModel)
        .filter(AnamnesisModel.student_id == STUDENT_ID)
        .order_by(AnamnesisModel.id)
        .all()
    )
    print(f"anamnesis count={len(anams)}")
    for r in anams:
        print(
            f"  id={r.id} v={r.version} name={r.student_full_name!r} "
            f"born={r.born_date} school={r.school_name!r} course={r.current_schooling!r} "
            f"address={r.address!r} phone={r.phone!r}"
        )

    folders = (
        db.query(FolderModel)
        .filter(
            FolderModel.student_id == STUDENT_ID,
            FolderModel.document_id == ANAMNESIS_DOCUMENT_ID,
        )
        .order_by(FolderModel.id)
        .all()
    )
    print(f"folders count={len(folders)}")
    for f in folders:
        print(
            f"  folder_id={f.id} file={f.file!r} detail_id={f.detail_id} "
            f"version_id={f.version_id} period={f.period_year}"
        )
        try:
            jobs = db.execute(
                text(
                    "SELECT * FROM student_drive_sync_jobs "
                    "WHERE folder_id = :fid ORDER BY id DESC"
                ),
                {"fid": int(f.id)},
            ).mappings().all()
            for j in jobs:
                print(f"    job={dict(j)}")
        except Exception as exc:
            print(f"    job_err={exc}")

    latest = anams[-1] if anams else None
    if latest:
        data = AnamnesisClass(db).get(int(latest.id))
        if isinstance(data, dict):
            filled = {
                k: v
                for k, v in data.items()
                if v not in (None, "", [], {}) and k not in {"status", "message"}
            }
            print(f"campos_con_valor={len(filled)}")
            for k in sorted(filled)[:40]:
                print(f"  {k}={filled[k]!r}"[:180])

    # Verificar archivo en Drive del último job
    last_job = db.execute(
        text(
            "SELECT drive_file_id FROM student_drive_sync_jobs "
            "WHERE drive_file_id IS NOT NULL ORDER BY id DESC LIMIT 1"
        )
    ).first()
    if last_job and last_job[0]:
        fid = last_job[0]
        cfg = load_customer_drive_config(db, 2)
        svc = _service_for_config(cfg)
        meta = svc.files().get(
            fileId=fid, fields="id,name,size,mimeType,trashed", supportsAllDrives=True
        ).execute()
        print(f"drive_meta={meta}")
    db.close()


if __name__ == "__main__":
    main()
