# -*- coding: utf-8 -*-
from sqlalchemy import text

from app.backend.db.database import SessionLocal

db = SessionLocal()
try:
    rows = db.execute(
        text(
            "SHOW INDEX FROM dynamic_form_submissions "
            "WHERE Key_name='uq_dynamic_form_student'"
        )
    ).fetchall()
    if rows:
        db.execute(text("ALTER TABLE dynamic_form_submissions DROP INDEX uq_dynamic_form_student"))
        print("dropped uq_dynamic_form_student")
    else:
        print("no uq_dynamic_form_student")

    cols = {r[0] for r in db.execute(text("SHOW COLUMNS FROM dynamic_form_submissions")).fetchall()}
    if "specialty" not in cols:
        db.execute(
            text(
                "ALTER TABLE dynamic_form_submissions "
                "ADD COLUMN specialty varchar(255) DEFAULT NULL AFTER period_year"
            )
        )
        print("added specialty")
    if "respondent_name" not in cols:
        db.execute(
            text(
                "ALTER TABLE dynamic_form_submissions "
                "ADD COLUMN respondent_name varchar(255) DEFAULT NULL AFTER specialty"
            )
        )
        print("added respondent_name")

    idx = db.execute(
        text(
            "SHOW INDEX FROM dynamic_form_submissions "
            "WHERE Key_name='idx_dfs_form_student'"
        )
    ).fetchall()
    if not idx:
        db.execute(
            text(
                "ALTER TABLE dynamic_form_submissions "
                "ADD KEY idx_dfs_form_student (dynamic_form_id, student_id)"
            )
        )
        print("added idx_dfs_form_student")
    db.commit()
    print("ok")
finally:
    db.close()
