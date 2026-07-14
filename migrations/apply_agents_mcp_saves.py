"""Create agents_mcp_saves (MCP store_data payloads from agents).

Run from backend/:
  python migrations/apply_agents_mcp_saves.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine

SQL = """
CREATE TABLE IF NOT EXISTS agents_mcp_saves (
  id INT NOT NULL AUTO_INCREMENT,
  agent_id VARCHAR(64) NOT NULL,
  customer_id INT NOT NULL,
  student_id INT NOT NULL,
  document_id INT NOT NULL,
  payload_json TEXT NOT NULL,
  origin VARCHAR(32) NOT NULL DEFAULT 'agent',
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  folder_id INT NULL,
  download_url VARCHAR(512) NULL,
  file_name VARCHAR(255) NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  INDEX ix_agents_mcp_saves_agent_id (agent_id),
  INDEX ix_agents_mcp_saves_customer_id (customer_id),
  INDEX ix_agents_mcp_saves_agent_student_status (agent_id, student_id, status),
  INDEX ix_agents_mcp_saves_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def main() -> None:
    with engine.begin() as conn:
        tables = set(inspect(conn).get_table_names())
        if "agents_mcp_saves" in tables:
            print("ok: agents_mcp_saves already exists")
            return
        conn.execute(text(SQL))
        print("ok: created agents_mcp_saves")


if __name__ == "__main__":
    main()
