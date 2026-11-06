"""Lista carpetas hermanas de ANAMNESIS en Drive (customer 2)."""
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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.import_drive_anamnesis import _access_token

ANAM = "1GpG0_E1AwMKObwFoWzOAqWhu3JHhxpEl"


def main() -> None:
    eng = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    db = sessionmaker(bind=eng)()
    token = _access_token(db)
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(
        f"https://www.googleapis.com/drive/v3/files/{ANAM}",
        headers=headers,
        params={"fields": "id,name,parents", "supportsAllDrives": "true"},
        timeout=60,
    )
    r.raise_for_status()
    info = r.json()
    print("anamnesis", info)
    parents = info.get("parents") or []
    parent = parents[0] if parents else None
    if not parent:
        raise SystemExit("sin parent")
    # parent meta
    rp = requests.get(
        f"https://www.googleapis.com/drive/v3/files/{parent}",
        headers=headers,
        params={"fields": "id,name,parents", "supportsAllDrives": "true"},
        timeout=60,
    )
    print("parent", rp.json())
    q = f"'{parent}' in parents and trashed=false"
    page_token = None
    files = []
    while True:
        params = {
            "q": q,
            "fields": "nextPageToken,files(id,name,mimeType)",
            "pageSize": 100,
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
        files.extend(data.get("files") or [])
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    files = sorted(files, key=lambda x: (x.get("name") or "").lower())
    print(f"siblings={len(files)}")
    for f in files:
        kind = "DIR" if "folder" in (f.get("mimeType") or "") else "FILE"
        print(f"{kind:4} {f.get('name')}  | {f['id']}")

    # si hay carpeta psicopedagogica, listar 1 nivel
    for f in files:
        name = (f.get("name") or "").lower()
        if "psico" in name or "pedagog" in name:
            print("\n=== contents of", f.get("name"), "===")
            q2 = f"'{f['id']}' in parents and trashed=false"
            rr2 = requests.get(
                "https://www.googleapis.com/drive/v3/files",
                headers=headers,
                params={
                    "q": q2,
                    "fields": "files(id,name,mimeType)",
                    "pageSize": 100,
                    "supportsAllDrives": "true",
                    "includeItemsFromAllDrives": "true",
                },
                timeout=60,
            )
            kids = sorted((rr2.json() or {}).get("files") or [], key=lambda x: (x.get("name") or "").lower())
            for k in kids[:40]:
                kind = "DIR" if "folder" in (k.get("mimeType") or "") else "FILE"
                print(f"  {kind:4} {k.get('name')}  | {k['id']}")
            if len(kids) > 40:
                print(f"  ... +{len(kids)-40} more")
    db.close()


if __name__ == "__main__":
    main()
