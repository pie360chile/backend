"""Apply agents tables: token usage + rename agent_v2_* → agents_*.

Run from backend/:
  python migrations/apply_agents_tables.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine

CREATE_USAGE = """
CREATE TABLE IF NOT EXISTS agents_token_usage (
  id INT NOT NULL AUTO_INCREMENT,
  customer_id INT NOT NULL,
  school_id INT NULL,
  user_id INT NULL,
  agent_id VARCHAR(64) NULL,
  request_kind VARCHAR(32) NOT NULL,
  model VARCHAR(64) NOT NULL,
  prompt_tokens INT NOT NULL,
  completion_tokens INT NOT NULL,
  total_tokens INT NOT NULL,
  estimated_cost_usd DECIMAL(12, 6) NOT NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  INDEX ix_agents_token_usage_customer_id (customer_id),
  INDEX ix_agents_token_usage_school_id (school_id),
  INDEX ix_agents_token_usage_customer_created (customer_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

CREATE_BUDGETS = """
CREATE TABLE IF NOT EXISTS agents_customer_budgets (
  id INT NOT NULL AUTO_INCREMENT,
  customer_id INT NOT NULL,
  monthly_budget_usd DECIMAL(12, 4) NOT NULL,
  buffer_percent DECIMAL(5, 2) NOT NULL,
  updated_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_agents_customer_budgets_customer_id (customer_id),
  INDEX ix_agents_customer_budgets_customer_id (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def main() -> None:
    with engine.begin() as conn:
        tables = set(inspect(conn).get_table_names())
        print("before:", sorted(t for t in tables if "agent" in t.lower()))

        conn.execute(text(CREATE_USAGE))
        print("ok: agents_token_usage")

        conn.execute(text(CREATE_BUDGETS))
        print("ok: agents_customer_budgets")

        tables = set(inspect(conn).get_table_names())

        if "agent_v2_agents" in tables and "agents" in tables:
            cols = {c["name"] for c in inspect(conn).get_columns("agents")}
            if "openai_container_id" in cols and "agents_legacy_deprecated" not in tables:
                conn.execute(text("RENAME TABLE agents TO agents_legacy_deprecated"))
                print("ok: agents -> agents_legacy_deprecated")
                tables = set(inspect(conn).get_table_names())

        tables = set(inspect(conn).get_table_names())
        if "agent_v2_agents" in tables and "agents" not in tables:
            conn.execute(text("RENAME TABLE agent_v2_agents TO agents"))
            print("ok: agent_v2_agents -> agents")

        tables = set(inspect(conn).get_table_names())
        if "agent_v2_document_templates" in tables and "agents_document_templates" not in tables:
            conn.execute(text("RENAME TABLE agent_v2_document_templates TO agents_document_templates"))
            print("ok: agent_v2_document_templates -> agents_document_templates")
            try:
                conn.execute(
                    text(
                        "ALTER TABLE agents_document_templates "
                        "RENAME INDEX ix_agent_v2_document_templates_agent_id "
                        "TO ix_agents_document_templates_agent_id"
                    )
                )
                print("ok: renamed document templates index")
            except Exception as exc:
                print("index rename skipped:", exc)

        tables = set(inspect(conn).get_table_names())
        if "agents" in tables:
            cols = {c["name"] for c in inspect(conn).get_columns("agents")}
            if "customer_id" not in cols:
                conn.execute(text("ALTER TABLE agents ADD COLUMN customer_id INT NULL"))
                print("ok: agents.customer_id column")
            try:
                conn.execute(text("CREATE INDEX ix_agents_customer_id ON agents (customer_id)"))
            except Exception:
                pass
            try:
                conn.execute(
                    text("CREATE INDEX ix_agents_customer_id_name ON agents (customer_id, name)")
                )
            except Exception:
                pass

        tables = set(inspect(conn).get_table_names())
        print("after:", sorted(t for t in tables if "agent" in t.lower()))

        if "alembic_version" in tables:
            ver = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            print("alembic was:", ver)
            conn.execute(
                text(
                    "UPDATE alembic_version SET version_num = :v"
                ),
                {"v": "0014_agents_customer_id"},
            )
            print("alembic stamped to 0014_agents_customer_id")


if __name__ == "__main__":
    main()
