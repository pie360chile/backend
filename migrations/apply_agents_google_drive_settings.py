"""Add Google Drive columns to agents_app_settings.

Run from backend/:
  python migrations/apply_agents_google_drive_settings.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine

ALTERS = [
    (
        "google_drive_root_folder_id",
        "ALTER TABLE agents_app_settings ADD COLUMN google_drive_root_folder_id VARCHAR(255) NULL",
    ),
    (
        "google_service_account_json",
        "ALTER TABLE agents_app_settings ADD COLUMN google_service_account_json TEXT NULL",
    ),
]


def main() -> None:
    cols = {
        c["name"]
        for c in inspect(engine).get_columns("agents_app_settings")
    }
    with engine.begin() as conn:
        for name, sql in ALTERS:
            if name in cols:
                print(f"ok: agents_app_settings.{name} already exists")
                continue
            conn.execute(text(sql))
            print(f"ok: added agents_app_settings.{name}")

    cols = {
        c["name"]
        for c in inspect(engine).get_columns("agents_app_settings")
    }
    print("has root:", "google_drive_root_folder_id" in cols)
    print("has sa json:", "google_service_account_json" in cols)


if __name__ == "__main__":
    main()
