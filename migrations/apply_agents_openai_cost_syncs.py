"""Apply agents_openai_cost_syncs table for OpenAI Costs reconciliation.

Run from backend/:
  python migrations/apply_agents_openai_cost_syncs.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS agents_openai_cost_syncs (
  id INT NOT NULL AUTO_INCREMENT,
  synced_at DATETIME NOT NULL,
  month_start DATETIME NOT NULL,
  openai_cost_usd DECIMAL(12, 6) NOT NULL DEFAULT 0,
  pie_cost_usd DECIMAL(12, 6) NOT NULL DEFAULT 0,
  delta_usd DECIMAL(12, 6) NOT NULL DEFAULT 0,
  adjustment_usd DECIMAL(12, 6) NOT NULL DEFAULT 0,
  status VARCHAR(32) NOT NULL DEFAULT 'ok',
  message VARCHAR(512) NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  INDEX ix_agents_openai_cost_syncs_synced_at (synced_at),
  INDEX ix_agents_openai_cost_syncs_month_start (month_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def main() -> None:
    with engine.begin() as conn:
        tables = set(inspect(conn).get_table_names())
        if "agents_openai_cost_syncs" in tables:
            print("ok: agents_openai_cost_syncs already exists")
            return
        conn.execute(text(CREATE_SQL))
        print("ok: agents_openai_cost_syncs")


if __name__ == "__main__":
    main()
