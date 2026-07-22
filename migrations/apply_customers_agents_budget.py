"""Add customers.agents_budget_usd_max (presupuesto tokens USD para Agentes).

Run from backend/:
  python migrations/apply_customers_agents_budget.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine

ALTER_SQL = """
ALTER TABLE customers
  ADD COLUMN agents_budget_usd_max DECIMAL(12, 2) NULL
"""


def main() -> None:
    cols = {c["name"] for c in inspect(engine).get_columns("customers")}
    with engine.begin() as conn:
        if "agents_budget_usd_max" not in cols:
            conn.execute(text(ALTER_SQL))
            print("ok: added customers.agents_budget_usd_max")
        else:
            print("ok: customers.agents_budget_usd_max already exists")


if __name__ == "__main__":
    main()
