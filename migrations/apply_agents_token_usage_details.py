"""Ensure agents_token_usage exists and has input/output text columns.

Run from backend/:
  python migrations/apply_agents_token_usage_details.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS agents_token_usage (
  id INT NOT NULL AUTO_INCREMENT,
  customer_id INT NOT NULL,
  school_id INT NULL,
  user_id INT NULL,
  agent_id VARCHAR(64) NULL,
  request_kind VARCHAR(32) NOT NULL,
  model VARCHAR(64) NOT NULL,
  prompt_tokens INT NOT NULL DEFAULT 0,
  completion_tokens INT NOT NULL DEFAULT 0,
  total_tokens INT NOT NULL DEFAULT 0,
  estimated_cost_usd DECIMAL(12, 6) NOT NULL DEFAULT 0,
  input_text TEXT NULL,
  output_text TEXT NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  INDEX ix_agents_token_usage_customer_id (customer_id),
  INDEX ix_agents_token_usage_school_id (school_id),
  INDEX ix_agents_token_usage_customer_created (customer_id, created_at),
  INDEX ix_agents_token_usage_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def _add_column_if_missing(conn, table: str, column: str, ddl: str) -> None:
    cols = {c["name"] for c in inspect(engine).get_columns(table)}
    if column in cols:
        print(f"ok: {table}.{column} already exists")
        return
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
    print(f"ok: added {table}.{column}")


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text(CREATE_SQL))
        print("ok: agents_token_usage table")
        _add_column_if_missing(conn, "agents_token_usage", "input_text", "input_text TEXT NULL")
        _add_column_if_missing(conn, "agents_token_usage", "output_text", "output_text TEXT NULL")

    tables = set(inspect(engine).get_table_names())
    print("has table:", "agents_token_usage" in tables)


if __name__ == "__main__":
    main()
