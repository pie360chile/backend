import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)
os.environ["DATABASE_URL"] = "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.backend.classes.professional_class import ProfessionalClass

eng = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
db = sessionmaker(bind=eng)()

with eng.connect() as c:
    rows = c.execute(
        text(
            "SELECT id, rol, school_id, customer_id FROM rols "
            "WHERE LOWER(rol) LIKE '%profesional%' "
            "AND (deleted_status_id = 0 OR deleted_status_id IS NULL) "
            "ORDER BY id"
        )
    ).fetchall()
    print("profesional roles:")
    for r in rows:
        print(" ", r)

for sid in (None, 4, 5, 1):
    res = ProfessionalClass(db).get_all(page=1, items_per_page=3, school_id=sid)
    if isinstance(res, dict):
        print(
            "school",
            sid,
            "total",
            res.get("total_items"),
            "roles",
            sorted({(x.get("rol_name") or "") for x in (res.get("data") or [])}),
        )
    else:
        print("school", sid, "n", len(res or []))

# page=0 full list size school 4
res4 = ProfessionalClass(db).get_all(page=0, school_id=4)
print("school4 full", len(res4) if isinstance(res4, list) else res4)
db.close()
