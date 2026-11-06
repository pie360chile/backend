"""Probe sample ANAMNESIS PDFs for text/AcroForm."""
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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.import_drive_anamnesis import (
    _access_token,
    _download_drive_file,
    _list_anamnesis_pdfs,
    _pdf_text_and_fields,
)


def main() -> None:
    eng = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=eng)()
    token = _access_token(db)
    pdfs = _list_anamnesis_pdfs(db)
    print(f"total={len(pdfs)}")
    for i, p in enumerate(pdfs[:20]):
        content = _download_drive_file(token, p["id"])
        text, fields = _pdf_text_and_fields(content)
        keys = list(fields.keys())[:12]
        print(
            f"{i+1} name={p['name'][:55]!r} bytes={len(content)} "
            f"text={len(text or '')} acro={len(fields or {})} keys={keys}"
        )
    db.close()


if __name__ == "__main__":
    main()
