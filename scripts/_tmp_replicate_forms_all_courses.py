"""Replica formularios cuestionario (ids>=8) a TODOS los cursos de cada colegio."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)
TUNNEL = "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.backend.classes.dynamic_form_class import DynamicFormClass
from app.backend.db.models import DynamicFormModel

PERIOD_YEAR = 2026


def main() -> None:
    os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL
    eng = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    db = sessionmaker(bind=eng)()

    # plantillas: una por (school_id, name) — la primera creada (menor id)
    templates = (
        db.query(DynamicFormModel)
        .filter(
            DynamicFormModel.id >= 8,
            DynamicFormModel.period_year == PERIOD_YEAR,
            DynamicFormModel.deleted_date.is_(None),
        )
        .order_by(DynamicFormModel.school_id, DynamicFormModel.name, DynamicFormModel.id)
        .all()
    )
    by_key: dict[tuple[int, str], DynamicFormModel] = {}
    for t in templates:
        key = (int(t.school_id), t.name)
        if key not in by_key:
            by_key[key] = t

    print(f"templates={len(by_key)}")
    created = 0
    skipped = 0
    for (school_id, name), tmpl in by_key.items():
        courses = db.execute(
            text("SELECT id, course_name FROM courses WHERE school_id = :s ORDER BY id"),
            {"s": school_id},
        ).fetchall()
        fields = json.loads(tmpl.fields_json or "[]")
        print(f"\nschool={school_id} form={name!r} courses={len(courses)} fields={len(fields)}")
        for cid, cname in courses:
            exists = (
                db.query(DynamicFormModel)
                .filter(
                    DynamicFormModel.school_id == school_id,
                    DynamicFormModel.period_year == PERIOD_YEAR,
                    DynamicFormModel.name == name,
                    DynamicFormModel.course_id == int(cid),
                    DynamicFormModel.deleted_date.is_(None),
                )
                .first()
            )
            if exists:
                skipped += 1
                continue
            res = DynamicFormClass(db).store(
                {
                    "name": name,
                    "description": tmpl.description or "",
                    "fields": fields,
                    "periodYear": PERIOD_YEAR,
                    "courseId": int(cid),
                    "respondentTypeId": int(tmpl.respondent_type_id or 2),
                },
                school_id=school_id,
            )
            if res.get("status") == "success":
                created += 1
                if created <= 5 or created % 25 == 0:
                    print(f"  OK course={cid} {cname} id={res.get('id')}")
            else:
                print(f"  ERR course={cid} {cname} {res}")

    print(f"\nDONE created={created} skipped_existing={skipped}")
    # resumen
    for sid in (1, 2, 3, 4, 5):
        n_forms = (
            db.query(DynamicFormModel)
            .filter(
                DynamicFormModel.school_id == sid,
                DynamicFormModel.period_year == PERIOD_YEAR,
                DynamicFormModel.deleted_date.is_(None),
                DynamicFormModel.id >= 8,
            )
            .count()
        )
        n_courses = db.execute(
            text("SELECT COUNT(*) FROM courses WHERE school_id = :s"), {"s": sid}
        ).scalar()
        print(f"school {sid}: courses={n_courses} forms={n_forms}")
    db.close()


if __name__ == "__main__":
    main()
