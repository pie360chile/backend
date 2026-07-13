"""Add customers.openai_api_key for per-client OpenAI keys (agents).

Run from backend/:
  python migrations/apply_customers_openai_api_key.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine


def main() -> None:
    with engine.begin() as conn:
        cols = {c["name"] for c in inspect(conn).get_columns("customers")}
        if "openai_api_key" in cols:
            print("ok: customers.openai_api_key already exists")
            return
        conn.execute(
            text(
                "ALTER TABLE customers "
                "ADD COLUMN openai_api_key VARCHAR(512) NULL "
                "AFTER email"
            )
        )
        print("ok: added customers.openai_api_key")


if __name__ == "__main__":
    main()
