"""Busca carpetas/archivos psicopedagógicos en Drive (customer 2)."""
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


def main() -> None:
    eng = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    db = sessionmaker(bind=eng)()
    with eng.connect() as c:
        tables = [
            r[0]
            for r in c.execute(text("SHOW TABLES LIKE '%document%'")).fetchall()
        ]
        print("tables_documentish:", tables)
        for t in tables:
            cols = [r[0] for r in c.execute(text(f"SHOW COLUMNS FROM `{t}`")).fetchall()]
            if "name" in cols or "document" in ",".join(cols):
                try:
                    rows = c.execute(
                        text(
                            f"SELECT * FROM `{t}` WHERE CAST(id AS CHAR) IN ('26','27') "
                            f"OR LOWER(COALESCE(name,'')) LIKE '%psico%' LIMIT 20"
                        )
                    ).mappings().all()
                    if rows:
                        print(t, [dict(x) for x in rows][:10])
                except Exception as e:
                    print("skip", t, e)

    token = _access_token(db)
    headers = {"Authorization": f"Bearer {token}"}

    queries = [
        "mimeType='application/vnd.google-apps.folder' and name contains 'PSICO' and trashed=false",
        "mimeType='application/vnd.google-apps.folder' and name contains 'Psico' and trashed=false",
        "mimeType='application/vnd.google-apps.folder' and name contains 'psicopedagog' and trashed=false",
        "name contains 'PSICOPEDAGOG' and trashed=false",
        "name contains 'ANAMNESIS' and mimeType='application/vnd.google-apps.folder' and trashed=false",
    ]
    seen = set()
    for q in queries:
        print("\nQ:", q)
        page_token = None
        n = 0
        while True:
            params = {
                "q": q,
                "fields": "nextPageToken,files(id,name,mimeType,parents)",
                "pageSize": 50,
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
                "corpora": "allDrives",
            }
            if page_token:
                params["pageToken"] = page_token
            rr = requests.get(
                "https://www.googleapis.com/drive/v3/files",
                headers=headers,
                params=params,
                timeout=60,
            )
            if rr.status_code >= 400:
                print(" err", rr.status_code, rr.text[:300])
                break
            data = rr.json()
            for f in data.get("files") or []:
                if f["id"] in seen:
                    continue
                seen.add(f["id"])
                n += 1
                print(f"  {f.get('name')} | {f['id']} | parents={f.get('parents')}")
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        print(" hits_newish", n)

    # Listar raíz del shared drive si aparece parent de ANAMNESIS vía about/drives
    rd = requests.get(
        "https://www.googleapis.com/drive/v3/drives",
        headers=headers,
        params={"pageSize": 20},
        timeout=60,
    )
    print("\ndrives", rd.status_code, rd.text[:800])
    db.close()


if __name__ == "__main__":
    main()
