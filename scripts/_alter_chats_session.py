import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from app.backend.db.database import SessionLocal

db = SessionLocal()
try:
    cols = db.execute(text("SHOW COLUMNS FROM chats LIKE 'session_id'")).fetchall()
    if not cols:
        db.execute(
            text(
                "ALTER TABLE chats ADD COLUMN session_id VARCHAR(64) NULL "
                "COMMENT 'Sesion anonima agente' AFTER customer_id"
            )
        )
        db.execute(text("ALTER TABLE chats ADD KEY idx_chats_session (session_id)"))
        db.commit()
        print("session_id column added")
    else:
        print("session_id already exists")
finally:
    db.close()
