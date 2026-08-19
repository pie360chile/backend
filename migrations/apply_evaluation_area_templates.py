"""Apply evaluation_area_templates table.

Run from backend/:
  python migrations/apply_evaluation_area_templates.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS evaluation_area_templates (
  id INT NOT NULL AUTO_INCREMENT,
  customer_id INT NOT NULL,
  area_id VARCHAR(64) NOT NULL,
  name VARCHAR(255) NOT NULL,
  original_filename VARCHAR(255) NOT NULL,
  stored_path VARCHAR(512) NOT NULL,
  content_type VARCHAR(128) NULL,
  uploaded_by INT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_evaluation_area_templates_customer_area_name (customer_id, area_id, name),
  INDEX ix_evaluation_area_templates_customer_id (customer_id),
  INDEX ix_evaluation_area_templates_area_id (area_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text(CREATE_SQL))
        print("ok: evaluation_area_templates")
        tables = set(inspect(conn).get_table_names())
        if "alembic_version" in tables:
            conn.execute(
                text("UPDATE alembic_version SET version_num = :v"),
                {"v": "0016_evaluation_area_templates"},
            )
            print("alembic stamped to 0016_evaluation_area_templates")


if __name__ == "__main__":
    main()
