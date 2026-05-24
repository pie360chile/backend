import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from app.backend.db.database import SessionLocal

db = SessionLocal()
try:
    chats = db.execute(text("SHOW TABLES LIKE 'chats'")).fetchall()
    details = db.execute(text("SHOW TABLES LIKE 'chat_details'")).fetchall()
    print("tables chats:", chats)
    print("tables chat_details:", details)
    if chats:
        n1 = db.execute(text("SELECT COUNT(*) FROM chats")).scalar()
        n2 = db.execute(text("SELECT COUNT(*) FROM chat_details")).scalar()
        print("counts chats/chat_details:", n1, n2)
        rows = db.execute(
            text(
                "SELECT id, chat_id, chat_type_id, LEFT(message, 80) AS msg "
                "FROM chat_details ORDER BY id DESC LIMIT 5"
            )
        ).fetchall()
        for r in rows:
            print(r)
finally:
    db.close()
