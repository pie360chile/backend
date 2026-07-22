"""Drop customers.openai_api_key (legacy; agents use DeepSeek llm_api_key in settings).

Run from backend/:
  python migrations/apply_customers_openai_api_key.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine


def main() -> None:
    with engine.begin() as conn:
        cols = {c["name"] for c in inspect(conn).get_columns("customers")}
        if "openai_api_key" not in cols:
            print("ok: customers.openai_api_key already absent")
            return
        conn.execute(text("ALTER TABLE customers DROP COLUMN openai_api_key"))
        print("ok: dropped customers.openai_api_key")


if __name__ == "__main__":
    main()
