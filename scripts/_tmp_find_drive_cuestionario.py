"""Busca en Drive archivos/carpetas 'cuestionario' (idealmente 14 oct)."""
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


def search(headers, q: str):
    out = []
    page_token = None
    while True:
        params = {
            "q": q,
            "fields": "nextPageToken,files(id,name,mimeType,parents,modifiedTime,createdTime,webViewLink)",
            "pageSize": 100,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "corpora": "allDrives",
            "orderBy": "modifiedTime desc",
        }
        if page_token:
            params["pageToken"] = page_token
        rr = requests.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params=params,
            timeout=90,
        )
        if rr.status_code >= 400:
            print("ERR", rr.status_code, rr.text[:400])
            return out
        data = rr.json()
        out.extend(data.get("files") or [])
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return out


def resolve_path(headers, file_id: str, depth: int = 6) -> str:
    parts = []
    cur = file_id
    for _ in range(depth):
        r = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{cur}",
            headers=headers,
            params={"fields": "id,name,parents", "supportsAllDrives": "true"},
            timeout=60,
        )
        if r.status_code >= 400:
            break
        info = r.json()
        parts.append(info.get("name") or "?")
        parents = info.get("parents") or []
        if not parents:
            break
        cur = parents[0]
    return " / ".join(reversed(parts))


def main() -> None:
    eng = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    db = sessionmaker(bind=eng)()
    token = _access_token(db)
    headers = {"Authorization": f"Bearer {token}"}

    queries = [
        "name contains 'cuestionario' and trashed=false",
        "name contains 'Cuestionario' and trashed=false",
        "name contains 'CUESTIONARIO' and trashed=false",
        "fullText contains 'cuestionario' and trashed=false",
    ]
    seen = set()
    rows = []
    for q in queries:
        print("Q:", q)
        for f in search(headers, q):
            if f["id"] in seen:
                continue
            seen.add(f["id"])
            rows.append(f)
        print("  unique so far", len(rows))

    # priorizar por fecha 14 oct / octubre / 10-14 / 14-10
    def score(f):
        name = (f.get("name") or "").lower()
        mt = f.get("modifiedTime") or ""
        ct = f.get("createdTime") or ""
        s = 0
        if "14" in name and ("oct" in name or "10" in name):
            s += 5
        if "2025-10-14" in mt or "2026-10-14" in mt or "2024-10-14" in mt:
            s += 10
        if "2025-10-14" in ct or "2026-10-14" in ct or "2024-10-14" in ct:
            s += 8
        if "10-14" in mt or "10-14" in ct:
            s += 3
        if "cuestionario" in name:
            s += 2
        return s

    rows.sort(key=lambda f: (-score(f), f.get("modifiedTime") or ""), reverse=False)
    rows.sort(key=lambda f: (-score(f), f.get("modifiedTime") or ""))

    print(f"\nTOTAL {len(rows)}")
    # show top / all if small
    show = rows[:60]
    for f in show:
        kind = "DIR" if "folder" in (f.get("mimeType") or "") else "FILE"
        path = resolve_path(headers, f["id"])
        print(
            f"{kind:4} score={score(f)} | {f.get('name')}\n"
            f"     modified={f.get('modifiedTime')} created={f.get('createdTime')}\n"
            f"     path={path}\n"
            f"     id={f['id']}"
        )

    # filtrar explícitamente 14 de octubre en timestamps
    oct14 = [
        f
        for f in rows
        if "10-14" in (f.get("modifiedTime") or "")
        or "10-14" in (f.get("createdTime") or "")
        or ("14" in (f.get("name") or "") and "oct" in (f.get("name") or "").lower())
    ]
    print(f"\n=== match 14 oct (fecha o nombre) n={len(oct14)} ===")
    for f in oct14[:40]:
        print("-", f.get("name"), "|", f.get("modifiedTime"), "|", f["id"])

    db.close()


if __name__ == "__main__":
    main()
