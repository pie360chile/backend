"""Quita professional_id mal matcheado (solo compartía nombre Carolina)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TUNNEL = "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
os.environ["DATABASE_URL"] = TUNNEL
os.environ["IMPORT_DATABASE_URL"] = TUNNEL

# Evitar que dotenv pise a remoto
import dotenv

dotenv.load_dotenv = lambda *a, **k: False  # type: ignore

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.backend.classes.anamnesis_class import AnamnesisClass

os.environ["DATABASE_URL"] = TUNNEL
eng = create_engine(TUNNEL, pool_pre_ping=True)
db = sessionmaker(bind=eng)()
print("url", eng.url)

# update directo por SQL por si AnamnesisClass falla
db.execute(
    text(
        "UPDATE anamnesis_interviewers SET professional_id = NULL "
        "WHERE anamnesis_id = 98"
    )
)
db.commit()
rows = db.execute(
    text("SELECT id, professional_id, role, interview_date FROM anamnesis_interviewers WHERE anamnesis_id=98")
).mappings().all()
print("rows", [dict(r) for r in rows])

# también vía class para consistencia
cur = AnamnesisClass(db).get(98) or {}
upd = {
    "interviewers": [
        {
            "sort_order": 0,
            "professional_id": None,
            "role": "Ed. diferencial",
            "interview_date": "2026-03-16",
        }
    ]
}
for k in ("informants", "household_members"):
    if cur.get(k) is not None:
        upd[k] = cur[k]
print(AnamnesisClass(db).update(98, upd))
print("verify", AnamnesisClass(db).get(98).get("interviewers"))
db.close()
