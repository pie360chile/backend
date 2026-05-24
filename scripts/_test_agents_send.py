import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from sqlalchemy import text
from app.backend.db.database import SessionLocal
from app.backend.classes.agents_class import AgentsClass

db = SessionLocal()
try:
    user_id = db.execute(text("SELECT id FROM users ORDER BY id ASC LIMIT 1")).scalar()
    print("test user_id:", user_id)
    if not user_id:
        print("no users in DB")
        raise SystemExit(1)

    result = AgentsClass(db).send_message(
        user_id=int(user_id),
        customer_id=None,
        message="Hola, prueba de guardado Agente Pie",
    )
    print("send_message result status:", result.get("status"), "chat_id:", result.get("chat_id") or result.get("id"))
    if result.get("status") == "error":
        print("error:", result.get("message"))
        raise SystemExit(1)

    n1 = db.execute(text("SELECT COUNT(*) FROM chats")).scalar()
    n2 = db.execute(text("SELECT COUNT(*) FROM chat_details")).scalar()
    print("counts after send:", n1, n2)

    rows = db.execute(
        text(
            "SELECT id, chat_id, chat_type_id, LEFT(message, 100) "
            "FROM chat_details ORDER BY id DESC LIMIT 4"
        )
    ).fetchall()
    for r in rows:
        print(r)
finally:
    db.close()
