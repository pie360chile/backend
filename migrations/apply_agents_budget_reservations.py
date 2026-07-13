"""Apply agents_budget_reservations table for parallel budget holds.

Run from backend/:
  python migrations/apply_agents_budget_reservations.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS agents_budget_reservations (
  id INT NOT NULL AUTO_INCREMENT,
  customer_id INT NOT NULL,
  reservation_key VARCHAR(64) NOT NULL,
  amount_usd DECIMAL(12, 6) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  expires_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_agents_budget_reservations_key (reservation_key),
  INDEX ix_agents_budget_reservations_customer_id (customer_id),
  INDEX ix_agents_budget_reservations_expires_at (expires_at),
  INDEX ix_agents_budget_reservations_customer_expires (customer_id, expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def main() -> None:
    with engine.begin() as conn:
        tables = set(inspect(conn).get_table_names())
        if "agents_budget_reservations" in tables:
            print("ok: agents_budget_reservations already exists")
            return
        conn.execute(text(CREATE_SQL))
        print("ok: agents_budget_reservations")


if __name__ == "__main__":
    main()
