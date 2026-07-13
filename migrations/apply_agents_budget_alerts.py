"""Apply agents_budget_alerts table (50/80/100% spend alerts).

Run from backend/:
  python migrations/apply_agents_budget_alerts.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS agents_budget_alerts (
  id INT NOT NULL AUTO_INCREMENT,
  customer_id INT NOT NULL,
  user_id INT NOT NULL,
  month_start DATETIME NOT NULL,
  threshold_percent INT NOT NULL,
  spent_usd DECIMAL(12, 6) NOT NULL DEFAULT 0,
  budget_usd DECIMAL(12, 4) NOT NULL DEFAULT 0,
  title VARCHAR(255) NOT NULL,
  message VARCHAR(1024) NOT NULL,
  status_id INT NOT NULL DEFAULT 0,
  email_sent INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  reviewed_at DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_agents_budget_alerts_user_month_threshold
    (customer_id, user_id, month_start, threshold_percent),
  INDEX ix_agents_budget_alerts_customer_id (customer_id),
  INDEX ix_agents_budget_alerts_user_id (user_id),
  INDEX ix_agents_budget_alerts_user_status (user_id, status_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def main() -> None:
    with engine.begin() as conn:
        tables = set(inspect(conn).get_table_names())
        if "agents_budget_alerts" in tables:
            print("ok: agents_budget_alerts already exists")
            return
        conn.execute(text(CREATE_SQL))
        print("ok: agents_budget_alerts")


if __name__ == "__main__":
    main()
