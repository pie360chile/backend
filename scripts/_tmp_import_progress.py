from app.backend.db.database import get_db
from sqlalchemy import text
db=next(get_db())
r=db.execute(text("SELECT COUNT(*) AS c FROM folders WHERE `file` LIKE :p"), {"p": "%legacy_2026%"}).fetchone()
print("folders_legacy", r[0])
rows=db.execute(text("SELECT id, student_id, document_id, `file`, added_date FROM folders WHERE `file` LIKE :p ORDER BY id DESC LIMIT 10"), {"p": "%legacy_2026%"}).fetchall()
for x in rows:
    print(x)
# also count by today
r2=db.execute(text("SELECT COUNT(*) FROM folders WHERE `file` LIKE :p AND added_date >= :d"), {"p": "%legacy_2026%", "d": "2026-09-02"}).fetchone()
print("today", r2[0])
