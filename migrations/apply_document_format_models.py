"""Apply document_format_models table.

Run from backend/:
  python migrations/apply_document_format_models.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS document_format_models (
  id INT NOT NULL AUTO_INCREMENT,
  document_id INT NOT NULL,
  original_filename VARCHAR(255) NOT NULL,
  stored_path VARCHAR(512) NOT NULL,
  content_type VARCHAR(128) NULL,
  uploaded_by INT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_document_format_models_document_id (document_id),
  INDEX ix_document_format_models_document_id (document_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text(CREATE_SQL))
        print("ok: document_format_models")
        tables = set(inspect(conn).get_table_names())
        if "alembic_version" in tables:
            conn.execute(
                text("UPDATE alembic_version SET version_num = :v"),
                {"v": "0015_document_format_models"},
            )
            print("alembic stamped to 0015_document_format_models")


if __name__ == "__main__":
    main()
