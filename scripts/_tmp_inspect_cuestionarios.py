"""Inspecciona hojas 'Cuestionario ... (respuestas)' y filas ~14 oct."""
from __future__ import annotations

import csv
import io
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

SHEETS = [
    ("1l71fakh1GoZsMPOXKDWSmD3uJfHXX40421uXNnDkXLw", "Cuestionario de Observación Especialistas Media (respuestas)"),
    ("1GD6POKJQy1DlJKRF2Vfr915KIKKXOBoLphQKoqf9y98", "Cuestionario de Observación Familiar Media (respuestas)"),
    ("1XjT9N5K70BCKlPwQD-3lVSUYP9DBDgq9uOwPsacGPJU", "Cuestionario Especialistas Básica (respuestas)"),
    ("1WYWa8Dzat97XOyhdUvsS-60WAoUeuwQsRpY8zxy8etY", "Cuestionario de Observación Psicopedagógica Media (respuestas)"),
    ("1gICYyc_RPVkFldSwmcJ9oISX0tzCgBPNzGIMl9mIIYE", "Cuestionario Básica Contexto Escolar (respuestas)"),
    ("1EPhSKX7e26wxDa3AUg5x1EBpKTkKUOffMKzOC0d8Iz8", "Cuestionario de Observación Familiar (respuestas)"),
]


def export_csv(headers, file_id: str) -> str:
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
    r = requests.get(
        url,
        headers=headers,
        params={"mimeType": "text/csv"},
        timeout=120,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code} {r.text[:300]}")
    return r.text


def main() -> None:
    eng = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    db = sessionmaker(bind=eng)()
    token = _access_token(db)
    headers = {"Authorization": f"Bearer {token}"}

    # también buscar archivos modificados exactamente el 14 oct 2026 con cuestionario en nombre
    q = (
        "name contains 'Cuestionario' and trashed=false "
        "and modifiedTime >= '2026-10-14T00:00:00Z' and modifiedTime < '2026-10-15T00:00:00Z'"
    )
    rr = requests.get(
        "https://www.googleapis.com/drive/v3/files",
        headers=headers,
        params={
            "q": q,
            "fields": "files(id,name,mimeType,modifiedTime,createdTime)",
            "pageSize": 100,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "corpora": "allDrives",
        },
        timeout=60,
    )
    print("modified exactamente 14-oct-2026:", rr.status_code, rr.json())

    out_dir = ROOT / "scripts" / "output" / "cuestionarios"
    out_dir.mkdir(parents=True, exist_ok=True)

    for fid, title in SHEETS:
        print("\n====", title, "====")
        try:
            text = export_csv(headers, fid)
        except Exception as e:
            print("export fail", e)
            continue
        path = out_dir / f"{fid[:8]}.csv"
        path.write_text(text, encoding="utf-8")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        print("rows", len(rows), "cols", len(rows[0]) if rows else 0)
        if rows:
            print("header[:8]:", rows[0][:8])
        # buscar timestamps 14/10 o 2026-10-14
        hit = 0
        samples = []
        for i, row in enumerate(rows[1:], start=2):
            joined = " | ".join(row[:3])
            low = joined.lower()
            if (
                "14/10/2026" in joined
                or "14-10-2026" in joined
                or "2026-10-14" in joined
                or "14/10/2025" in joined
                or "2025-10-14" in joined
                or "/10/14" in low
            ):
                hit += 1
                if len(samples) < 5:
                    samples.append((i, row[:6]))
        print("filas con fecha 14 oct:", hit)
        for s in samples:
            print(" ", s)
        # mostrar primeras 3 marcas de tiempo
        for row in rows[1:4]:
            print(" sample_ts:", row[:2] if row else None)

    db.close()


if __name__ == "__main__":
    main()
