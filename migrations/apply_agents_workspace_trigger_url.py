"""Add agents.workspace_trigger_url (endpoint Workspace ChatGPT por agente).

Run from backend/:
  python migrations/apply_agents_workspace_trigger_url.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine

SQL = """
ALTER TABLE agents
  ADD COLUMN workspace_trigger_url TEXT NULL
"""


def main() -> None:
    cols = {c["name"] for c in inspect(engine).get_columns("agents")}
    with engine.begin() as conn:
        if "workspace_trigger_url" in cols:
            print("ok: agents.workspace_trigger_url already exists")
        else:
            conn.execute(text(SQL))
            print("ok: added agents.workspace_trigger_url")


if __name__ == "__main__":
    main()
