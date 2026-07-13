"""Apply agents_rate_limit_hits for chat request throttling.

Run from backend/:
  python migrations/apply_agents_rate_limits.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS agents_rate_limit_hits (
  id INT NOT NULL AUTO_INCREMENT,
  user_id INT NULL,
  customer_id INT NULL,
  school_id INT NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  INDEX ix_agents_rate_limit_hits_user_id (user_id),
  INDEX ix_agents_rate_limit_hits_customer_id (customer_id),
  INDEX ix_agents_rate_limit_hits_school_id (school_id),
  INDEX ix_agents_rate_limit_hits_created_at (created_at),
  INDEX ix_agents_rate_limit_hits_user_created (user_id, created_at),
  INDEX ix_agents_rate_limit_hits_customer_created (customer_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def main() -> None:
    with engine.begin() as conn:
        tables = set(inspect(conn).get_table_names())
        if "agents_rate_limit_hits" in tables:
            print("ok: agents_rate_limit_hits already exists")
            return
        conn.execute(text(CREATE_SQL))
        print("ok: agents_rate_limit_hits")


if __name__ == "__main__":
    main()
