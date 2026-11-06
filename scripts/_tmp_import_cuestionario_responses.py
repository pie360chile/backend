"""Importa respuestas de cuestionarios Drive → dynamic_form_submissions.

También elimina formularios de prueba (ids 1–7).

Uso:
  python scripts/_tmp_import_cuestionario_responses.py --delete-tests
  python scripts/_tmp_import_cuestionario_responses.py --apply
  python scripts/_tmp_import_cuestionario_responses.py --apply --limit 20
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)
TUNNEL = "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL
os.environ["IMPORT_DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.backend.classes.dynamic_form_class import DynamicFormClass
from app.backend.db.models import (
    CourseModel,
    DynamicFormModel,
    DynamicFormSubmissionModel,
    StudentAcademicInfoModel,
    StudentModel,
    StudentPersonalInfoModel,
)
from scripts._tmp_create_forms_from_cuestionarios import (
    CSV_DIR,
    FORM_MAP,
    PERIOD_YEAR,
    _is_skip_header,
    _parse_section_question,
    _slug,
    build_fields,
)
from scripts.import_drive_anamnesis import (
    _course_key_from_text,
    _match_student_by_name,
    _name_tokens,
    _norm_name,
)

CUSTOMER_ID = 2
PROGRESS = ROOT / "scripts" / "output" / "cuestionarios" / "responses_import.jsonl"

# cache: course_id -> set(student_id)
_COURSE_STUDENTS: dict[int, set[int]] = {}
# cache: (school_id, course_id, form_name) -> form_id
_FORM_CACHE: dict[tuple[int, int, str], int | None] = {}

# Texto establecimiento (Google Forms) → school_id PIE360
ESTAB_MAP = {
    "basica 1": 1,
    "basica los andes 1": 1,
    "basica 2": 2,
    "basica los andes 2": 2,
    "media los andes": 3,
    "basica san felipe": 4,
    "media san felipe": 5,
}

TEST_FORM_IDS = (1, 2, 3, 4, 5, 6, 7)


def _fix_txt(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return s
    try:
        if "Ã" in s or "Â" in s:
            return s.encode("latin1").decode("utf-8")
    except Exception:
        pass
    return s


def _norm(s: str) -> str:
    s = _fix_txt(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s)


def _estab_school_id(raw: str) -> int | None:
    n = _norm(raw)
    if not n:
        return None
    if n in ESTAB_MAP:
        return ESTAB_MAP[n]
    for key, sid in ESTAB_MAP.items():
        if key in n or n in key:
            return sid
    return None


def _find_col(headers: list[str], *needles: str) -> int | None:
    norms = [_norm(h) for h in headers]
    for needle in needles:
        nn = _norm(needle)
        for i, h in enumerate(norms):
            if nn in h:
                return i
    return None


def _col_field_map(headers: list[str]) -> list[tuple[int, str]]:
    """(col_idx, field_id) en el mismo orden que build_fields."""
    out: list[tuple[int, str]] = []
    for i, h in enumerate(headers):
        if _is_skip_header(h):
            continue
        section, question = _parse_section_question(h)
        fid = _slug(question or h, len(out) + 1)
        out.append((i, fid))
    return out


def _build_index(db) -> list[dict]:
    rows = (
        db.query(
            StudentModel.id,
            StudentPersonalInfoModel.names,
            StudentPersonalInfoModel.father_lastname,
            StudentPersonalInfoModel.mother_lastname,
            StudentAcademicInfoModel.course_id,
            CourseModel.course_name,
            CourseModel.school_id,
        )
        .outerjoin(
            StudentPersonalInfoModel,
            StudentPersonalInfoModel.student_id == StudentModel.id,
        )
        .outerjoin(
            StudentAcademicInfoModel,
            StudentAcademicInfoModel.student_id == StudentModel.id,
        )
        .outerjoin(CourseModel, CourseModel.id == StudentAcademicInfoModel.course_id)
        .filter(StudentModel.deleted_status_id == 0)
        .all()
    )
    out: list[dict] = []
    for sid, names, fl, ml, course_id, course_name, school_id in rows:
        full = " ".join(
            p for p in [(names or "").strip(), (fl or "").strip(), (ml or "").strip()] if p
        )
        if not full:
            continue
        tokens = _name_tokens(full)
        if len(tokens) < 2:
            continue
        cg, cl = _course_key_from_text(course_name or "")
        out.append(
            {
                "student_id": int(sid),
                "full_name": full,
                "tokens": tokens,
                "norm": _norm_name(full),
                "course_id": int(course_id) if course_id else None,
                "course_name": course_name or "",
                "course_grade": cg,
                "course_letter": cl,
                "school_id": int(school_id) if school_id else None,
            }
        )
    return out


def _log(row: dict) -> None:
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    with PROGRESS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _course_students(db, course_id: int, school_id: int) -> set[int]:
    if course_id in _COURSE_STUDENTS:
        return _COURSE_STUDENTS[course_id]
    res = DynamicFormClass(db).get_course_recipients(course_id, school_id, CUSTOMER_ID, PERIOD_YEAR)
    out: set[int] = set()
    if res.get("status") == "success":
        for r in res.get("data") or []:
            try:
                out.add(int(r.get("studentId")))
            except Exception:
                pass
    _COURSE_STUDENTS[course_id] = out
    return out


def _find_form_id(db, school_id: int, course_id: int, form_name: str) -> int | None:
    key = (school_id, course_id, form_name)
    if key in _FORM_CACHE:
        return _FORM_CACHE[key]
    form = (
        db.query(DynamicFormModel.id)
        .filter(
            DynamicFormModel.school_id == school_id,
            DynamicFormModel.course_id == course_id,
            DynamicFormModel.period_year == PERIOD_YEAR,
            DynamicFormModel.name == form_name,
            DynamicFormModel.deleted_date.is_(None),
        )
        .first()
    )
    fid = int(form[0]) if form else None
    _FORM_CACHE[key] = fid
    return fid


def _upsert_submission(
    db,
    *,
    form_id: int,
    student_id: int,
    school_id: int,
    answers: dict,
    specialty: str | None,
    respondent_name: str | None,
) -> int:
    """Inserta/actualiza sin revalidar recipients en cada fila."""
    now = datetime.now()
    payload = json.dumps(answers, ensure_ascii=False)
    spec = (specialty or "").strip() or None
    resp = (respondent_name or "").strip() or None
    q = db.query(DynamicFormSubmissionModel).filter(
        DynamicFormSubmissionModel.dynamic_form_id == form_id,
        DynamicFormSubmissionModel.student_id == student_id,
    )
    if spec:
        q = q.filter(DynamicFormSubmissionModel.specialty == spec)
    else:
        q = q.filter(
            (DynamicFormSubmissionModel.specialty.is_(None))
            | (DynamicFormSubmissionModel.specialty == "")
        )
    if resp:
        q = q.filter(DynamicFormSubmissionModel.respondent_name == resp)
    else:
        q = q.filter(
            (DynamicFormSubmissionModel.respondent_name.is_(None))
            | (DynamicFormSubmissionModel.respondent_name == "")
        )
    existing = q.first()
    if existing:
        existing.answers_json = payload
        existing.specialty = spec
        existing.respondent_name = resp
        existing.updated_date = now
        db.commit()
        return int(existing.id)
    row = DynamicFormSubmissionModel(
        dynamic_form_id=form_id,
        student_id=student_id,
        school_id=school_id,
        period_year=PERIOD_YEAR,
        specialty=spec,
        respondent_name=resp,
        answers_json=payload,
        submitted_by_user_id=None,
        added_date=now,
        updated_date=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return int(row.id)


def delete_tests(db) -> None:
    n_sub = (
        db.query(DynamicFormSubmissionModel)
        .filter(DynamicFormSubmissionModel.dynamic_form_id.in_(TEST_FORM_IDS))
        .delete(synchronize_session=False)
    )
    # hard delete test forms (ya soft-deleted o activos)
    n_form = (
        db.query(DynamicFormModel)
        .filter(DynamicFormModel.id.in_(TEST_FORM_IDS))
        .delete(synchronize_session=False)
    )
    db.commit()
    print(f"deleted_test_forms={n_form} submissions={n_sub} ids={TEST_FORM_IDS}", flush=True)


def _row_answers(row: list[str], col_map: list[tuple[int, str]]) -> dict:
    answers: dict = {}
    for col, fid in col_map:
        if col >= len(row):
            continue
        val = _fix_txt(row[col]).strip()
        if not val:
            continue
        # Sí variants
        if _norm(val) in {"si", "s"}:
            val = "Sí"
        answers[fid] = val
    return answers


def import_csv(
    db,
    index: list[dict],
    stem: str,
    form_name: str,
    school_ids: list[int],
    *,
    apply: bool,
    limit: int | None,
) -> dict:
    path = CSV_DIR / f"{stem}.csv"
    if not path.exists():
        return {"stem": stem, "error": "missing csv"}

    raw_rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
    if not raw_rows:
        return {"stem": stem, "error": "empty"}
    headers = raw_rows[0]
    data = raw_rows[1:]
    col_map = _col_field_map(headers)
    # sanity vs build_fields ids
    fields = build_fields(path)
    field_ids = [f["id"] for f in fields]
    map_ids = [fid for _, fid in col_map]
    if field_ids != map_ids:
        print(f"WARN {stem}: field id mismatch fields={len(field_ids)} map={len(map_ids)}", flush=True)

    i_est = _find_col(headers, "establecimiento")
    i_name = _find_col(
        headers,
        "nombre completo del/la estudiante",
        "nombre del estudiante",
        "nombre del/la estudiante",
        "nombre estudiante",
    )
    i_curso = _find_col(headers, "curso del estudiante", "curso")
    i_resp = _find_col(
        headers,
        "nombre de quien responde",
        "nombre del/la especialista",
        "nombre docente",
        "nombre del/la",
    )
    i_spec = _find_col(headers, "especialidad", "asignatura o rol", "rol en el establecimiento")

    stats = {
        "stem": stem,
        "form": form_name,
        "rows": 0,
        "ok": 0,
        "skip_blank": 0,
        "not_found": 0,
        "ambiguous": 0,
        "no_form": 0,
        "error": 0,
        "dry": 0,
    }

    processed = 0
    for row in data:
        if i_name is None or i_name >= len(row):
            stats["skip_blank"] += 1
            continue
        student_name = _fix_txt(row[i_name]).strip()
        if not student_name:
            stats["skip_blank"] += 1
            continue
        stats["rows"] += 1
        if limit is not None and processed >= limit:
            break
        processed += 1

        estab = _fix_txt(row[i_est]).strip() if i_est is not None and i_est < len(row) else ""
        sid_school = _estab_school_id(estab)
        allowed_schools = [sid_school] if sid_school in school_ids else list(school_ids)
        if sid_school and sid_school not in school_ids:
            # establecimiento fuera del mapa del form
            allowed_schools = list(school_ids)

        curso_txt = _fix_txt(row[i_curso]).strip() if i_curso is not None and i_curso < len(row) else ""
        cg, cl = _course_key_from_text(curso_txt)

        scoped = [r for r in index if r.get("school_id") in allowed_schools]
        status, ids, detail = _match_student_by_name(
            student_name, scoped, course_grade=cg, course_letter=cl
        )
        if status == "not_found":
            # retry without course constraint
            status2, ids2, detail2 = _match_student_by_name(student_name, scoped)
            if status2 == "ok":
                status, ids, detail = status2, ids2, detail2 + " (no-course)"
            else:
                stats["not_found"] += 1
                _log(
                    {
                        "status": "not_found",
                        "form": form_name,
                        "name": student_name,
                        "curso": curso_txt,
                        "estab": estab,
                        "detail": detail,
                    }
                )
                continue
        if status == "ambiguous":
            stats["ambiguous"] += 1
            _log(
                {
                    "status": "ambiguous",
                    "form": form_name,
                    "name": student_name,
                    "curso": curso_txt,
                    "estab": estab,
                    "detail": detail,
                    "ids": ids,
                }
            )
            continue

        student_id = int(ids[0])
        stu = next((r for r in index if r["student_id"] == student_id), None)
        course_id = stu.get("course_id") if stu else None
        school_id = stu.get("school_id") if stu else sid_school
        if not course_id or not school_id:
            stats["no_form"] += 1
            _log(
                {
                    "status": "no_course",
                    "form": form_name,
                    "name": student_name,
                    "student_id": student_id,
                }
            )
            continue

        form_id = _find_form_id(db, int(school_id), int(course_id), form_name)
        if not form_id:
            stats["no_form"] += 1
            _log(
                {
                    "status": "no_form",
                    "form": form_name,
                    "name": student_name,
                    "student_id": student_id,
                    "school_id": school_id,
                    "course_id": course_id,
                }
            )
            continue

        allowed = _course_students(db, int(course_id), int(school_id))
        if student_id not in allowed:
            stats["error"] += 1
            _log(
                {
                    "status": "not_in_course",
                    "form": form_name,
                    "form_id": form_id,
                    "student_id": student_id,
                    "name": student_name,
                    "course_id": course_id,
                }
            )
            continue

        answers = _row_answers(row, col_map)
        respondent = (
            _fix_txt(row[i_resp]).strip() if i_resp is not None and i_resp < len(row) else ""
        ) or None
        specialty = (
            _fix_txt(row[i_spec]).strip() if i_spec is not None and i_spec < len(row) else ""
        ) or None

        if not apply:
            stats["dry"] += 1
            _log(
                {
                    "status": "dry",
                    "form": form_name,
                    "form_id": form_id,
                    "student_id": student_id,
                    "name": student_name,
                    "answers": len(answers),
                    "respondent": respondent,
                    "specialty": specialty,
                }
            )
            continue

        try:
            sub_id = _upsert_submission(
                db,
                form_id=int(form_id),
                student_id=student_id,
                school_id=int(school_id),
                answers=answers,
                specialty=specialty,
                respondent_name=respondent,
            )
            stats["ok"] += 1
            if stats["ok"] % 50 == 0:
                print(f"  ... ok={stats['ok']}", flush=True)
            _log(
                {
                    "status": "ok",
                    "form": form_name,
                    "form_id": form_id,
                    "student_id": student_id,
                    "name": student_name,
                    "submission_id": sub_id,
                    "answers": len(answers),
                }
            )
        except Exception as e:
            db.rollback()
            stats["error"] += 1
            _log(
                {
                    "status": "error",
                    "form": form_name,
                    "form_id": form_id,
                    "student_id": student_id,
                    "name": student_name,
                    "error": str(e)[:300],
                }
            )

    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delete-tests", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="Solo simula import (default si no hay --apply)")
    ap.add_argument("--limit", type=int, default=None, help="Límite por CSV")
    ap.add_argument("--only-stem", action="append", default=[])
    ap.add_argument("--import-only", action="store_true", help="No borrar pruebas")
    args = ap.parse_args()

    os.environ["DATABASE_URL"] = TUNNEL
    eng = create_engine(TUNNEL, pool_pre_ping=True)
    db = sessionmaker(bind=eng)()

    do_delete = args.delete_tests or (args.apply and not args.import_only)
    do_import = args.apply or args.dry_run or (not args.delete_tests)

    if do_delete:
        delete_tests(db)

    if not do_import:
        print("listo (solo delete)", flush=True)
        db.close()
        eng.dispose()
        return

    apply = bool(args.apply)
    index = _build_index(db)
    print(f"student_index={len(index)} apply={apply}", flush=True)

    stems = args.only_stem or list(FORM_MAP.keys())
    for stem in stems:
        if stem not in FORM_MAP:
            print("unknown stem", stem)
            continue
        name, _respondent, school_ids = FORM_MAP[stem]
        print(f"\n=== {stem} {name} ===", flush=True)
        stats = import_csv(
            db,
            index,
            stem,
            name,
            school_ids,
            apply=apply,
            limit=args.limit,
        )
        print(json.dumps(stats, ensure_ascii=False), flush=True)

    db.close()
    eng.dispose()


if __name__ == "__main__":
    main()
