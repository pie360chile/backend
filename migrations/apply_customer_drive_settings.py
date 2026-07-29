"""Create customer_drive_settings (Google Drive OAuth por cliente).

Run from backend/:
  python migrations/apply_customer_drive_settings.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS customer_drive_settings (
  customer_id INT NOT NULL PRIMARY KEY,
  root_folder_id VARCHAR(255) NULL,
  credentials_json TEXT NULL,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
)
"""


def main() -> None:
    tables = set(inspect(engine).get_table_names())
    with engine.begin() as conn:
        if "customer_drive_settings" not in tables:
            conn.execute(text(CREATE_SQL))
            print("ok: created customer_drive_settings")
        else:
            print("ok: customer_drive_settings already exists")
            cols = {c["name"] for c in inspect(engine).get_columns("customer_drive_settings")}
            print("columns:", sorted(cols))


if __name__ == "__main__":
    main()
