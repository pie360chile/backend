"""Lista carpeta padre de informes psicopedagógicos y muestra un árbol breve."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)
os.environ["DATABASE_URL"] = (
    os.environ.get("IMPORT_DATABASE_URL")
    or "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
)

import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from scripts.import_drive_anamnesis import _access_token

PARENT = "1Iz-FO5InXmIg-_-4L9GhT2uQCY73xNjC"
PSICO_SF_BASICA = "1f5p6jgwks8-VRWGDdQ5O2Aq3MQOZIeHr"


def list_children(headers, folder_id: str, *, page_size: int = 100):
    out = []
    page_token = None
    while True:
        params = {
            "q": f"'{folder_id}' in parents and trashed=false",
            "fields": "nextPageToken,files(id,name,mimeType)",
            "pageSize": page_size,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        if page_token:
            params["pageToken"] = page_token
        rr = requests.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params=params,
            timeout=60,
        )
        rr.raise_for_status()
        data = rr.json()
        out.extend(data.get("files") or [])
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return sorted(out, key=lambda x: (x.get("name") or "").lower())


def main() -> None:
    eng = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    db = sessionmaker(bind=eng)()
    with eng.connect() as c:
        cols = [r[0] for r in c.execute(text("SHOW COLUMNS FROM documents")).fetchall()]
        print("documents cols:", cols)
        # try common name columns
        for col in ("document", "alias", "title", "description"):
            if col in cols:
                rows = c.execute(
                    text(
                        f"SELECT id, `{col}` FROM documents "
                        f"WHERE id IN (26,27) OR LOWER(`{col}`) LIKE '%psico%' LIMIT 20"
                    )
                ).fetchall()
                print("by", col, rows)

    token = _access_token(db)
    headers = {"Authorization": f"Bearer {token}"}
    meta = requests.get(
        f"https://www.googleapis.com/drive/v3/files/{PARENT}",
        headers=headers,
        params={"fields": "id,name", "supportsAllDrives": "true"},
        timeout=60,
    ).json()
    print("PARENT", meta)
    kids = list_children(headers, PARENT)
    print(f"children={len(kids)}")
    for f in kids:
        kind = "DIR" if "folder" in (f.get("mimeType") or "") else "FILE"
        print(f"  {kind:4} {f.get('name')} | {f['id']}")

    print("\n=== San Felipe Básica (sample tree) ===")
    lvl1 = list_children(headers, PSICO_SF_BASICA)
    print("top", len(lvl1))
    for f in lvl1[:25]:
        kind = "DIR" if "folder" in (f.get("mimeType") or "") else "FILE"
        print(f"  {kind:4} {f.get('name')}")
    # count pdfs recursively shallow: enter first 3 dirs
    pdf_n = 0
    sample_pdfs = []
    for f in lvl1:
        if "folder" in (f.get("mimeType") or ""):
            sub = list_children(headers, f["id"])
            for s in sub:
                if (s.get("name") or "").lower().endswith(".pdf"):
                    pdf_n += 1
                    if len(sample_pdfs) < 8:
                        sample_pdfs.append(f"{f.get('name')}/{s.get('name')}")
                elif "folder" in (s.get("mimeType") or ""):
                    sub2 = list_children(headers, s["id"])
                    for s2 in sub2:
                        if (s2.get("name") or "").lower().endswith(".pdf"):
                            pdf_n += 1
                            if len(sample_pdfs) < 8:
                                sample_pdfs.append(
                                    f"{f.get('name')}/{s.get('name')}/{s2.get('name')}"
                                )
    print("approx_pdfs_shallow", pdf_n)
    for p in sample_pdfs:
        print("  pdf", p)
    db.close()


if __name__ == "__main__":
    main()
