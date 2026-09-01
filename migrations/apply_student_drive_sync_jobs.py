"""Apply the persistent student document Drive sync queue.

Run from backend/:
  python migrations/apply_student_drive_sync_jobs.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS student_drive_sync_jobs (
  id INT NOT NULL AUTO_INCREMENT,
  folder_id INT NOT NULL,
  student_id INT NOT NULL,
  document_id INT NOT NULL,
  file_path VARCHAR(512) NOT NULL,
  mime_type VARCHAR(128) NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'pending',
  attempts INT NOT NULL DEFAULT 0,
  next_attempt_at DATETIME NOT NULL,
  locked_at DATETIME NULL,
  last_error TEXT NULL,
  drive_file_id VARCHAR(255) NULL,
  drive_path VARCHAR(1024) NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  completed_at DATETIME NULL,
  PRIMARY KEY (id),
  INDEX ix_student_drive_sync_jobs_folder_id (folder_id),
  INDEX ix_student_drive_sync_jobs_student_id (student_id),
  INDEX ix_student_drive_sync_jobs_status (status),
  INDEX ix_student_drive_sync_jobs_next_attempt_at (next_attempt_at),
  INDEX ix_student_drive_sync_jobs_due (status, next_attempt_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text(CREATE_SQL))
        print("ok: student_drive_sync_jobs")
        if "alembic_version" in set(inspect(conn).get_table_names()):
            conn.execute(
                text("UPDATE alembic_version SET version_num = :version"),
                {"version": "0017_student_drive_sync_jobs"},
            )
            print("alembic stamped to 0017_student_drive_sync_jobs")


if __name__ == "__main__":
    main()
