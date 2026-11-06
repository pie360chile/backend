"""Crea dynamic_forms desde cabeceras de cuestionarios Drive (sin datos personales PIE360)."""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter
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

CSV_DIR = ROOT / "scripts" / "output" / "cuestionarios"
PERIOD_YEAR = 2026

# csv_stem -> (nombre form, respondent_type 1=apoderado 2=profesional, school_ids)
FORM_MAP = {
    "1EPhSKX7": (
        "Cuestionario de Observación Familiar (Básica)",
        1,
        [1, 2, 4],
    ),
    "1GD6POKJ": (
        "Cuestionario de Observación Familiar (Media)",
        1,
        [3, 5],
    ),
    "1gICYyc_": (
        "Cuestionario Básica Contexto Escolar",
        2,
        [1, 2, 4],
    ),
    "1XjT9N5K": (
        "Cuestionario Especialistas Básica",
        2,
        [1, 2, 4],
    ),
    "1l71fakh": (
        "Cuestionario Especialistas Media",
        2,
        [3, 5],
    ),
    "1WYWa8Dz": (
        "Cuestionario de Observación Psicopedagógica Media",
        2,
        [3, 5],
    ),
}

# Cabeceras que NO van al formulario (ya están en ficha PIE360 / meta del envío)
SKIP_HEADER_RES = [
    r"^marca temporal$",
    r"^fecha de respuesta",
    r"^fecha de nacimiento",
    r"^establecimiento",
    r"^nombre (completo )?del/?la estudiante",
    r"^nombre del estudiante$",
    r"^curso del estudiante",
    r"^nombre de quien responde",
    r"^nombre docente",
    r"^nombre del/?la especialista",
    r"^parentesco",
    r"^especialidad$",
    r"^asignatura o rol",
    r"^rol en el establecimiento$",
]


def _fix_txt(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return s
    try:
        fixed = s.encode("latin1").decode("utf-8")
        if "Ã" in s or "Â" in s:
            return fixed
    except Exception:
        pass
    return s


def _norm(s: str) -> str:
    s = _fix_txt(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s)


def _is_skip_header(h: str) -> bool:
    n = _norm(h)
    for pat in SKIP_HEADER_RES:
        if re.search(pat, n):
            return True
    return False


def _slug(s: str, i: int) -> str:
    n = _norm(s)
    n = re.sub(r"[^a-z0-9]+", "_", n).strip("_")
    return f"f_{i:03d}_{n[:40]}"


def _parse_section_question(header: str) -> tuple[str | None, str]:
    h = _fix_txt(header).strip()
    m = re.match(r"^(.+?)\s*\[(.+)\]\s*$", h, flags=re.S)
    if m:
        section = re.sub(r"\s+", " ", m.group(1)).strip(" :")
        question = re.sub(r"\s+", " ", m.group(2)).strip()
        return section, question
    # "Seccion: [pregunta]" variant with colon before bracket already handled
    m2 = re.match(r"^(.+?):\s*(.+)$", h, flags=re.S)
    if m2 and "[" not in h and len(m2.group(1)) < 80:
        # only if left looks like section title
        left = m2.group(1).strip()
        if "habilidad" in _norm(left) or len(left.split()) <= 8:
            return left, m2.group(2).strip()
    return None, re.sub(r"\s+", " ", h)


LIKERT_3 = [
    {"label": "Lo hace con seguridad", "value": "Lo hace con seguridad"},
    {"label": "A veces lo logra", "value": "A veces lo logra"},
    {"label": "Necesita ayuda frecuentemente", "value": "Necesita ayuda frecuentemente"},
]
LOGRADO_3 = [
    {"label": "Logrado", "value": "Logrado"},
    {"label": "En proceso", "value": "En proceso"},
    {"label": "Requiere apoyo", "value": "Requiere apoyo"},
]
SI_NO = [
    {"label": "Sí", "value": "Sí"},
    {"label": "No", "value": "No"},
]


def _unique_vals(rows: list[list[str]], col: int, *, limit: int = 40) -> list[str]:
    c: Counter[str] = Counter()
    for r in rows:
        if len(r) <= col:
            continue
        v = _fix_txt(r[col]).strip()
        if not v:
            continue
        c[v] += 1
    return [v for v, _ in c.most_common(limit)]


def _options_from_vals(vals: list[str]) -> list[dict] | None:
    if not vals:
        return None
    # normalize Sí variants
    cleaned = []
    for v in vals:
        vn = _norm(v)
        if vn in {"si", "sí", "s"}:
            cleaned.append("Sí")
        elif vn == "no":
            cleaned.append("No")
        else:
            cleaned.append(v)
    # dedupe preserving order
    out = []
    seen = set()
    for v in cleaned:
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    if len(out) > 12:
        return None
    avg = sum(len(x) for x in out) / max(len(out), 1)
    if avg > 120 and len(out) > 4:
        return None
    return [{"label": x, "value": x} for x in out]


def build_fields(csv_path: Path) -> list[dict]:
    raw = csv_path.read_text(encoding="utf-8")
    rows = list(csv.reader(raw.splitlines()))
    if not rows:
        return []
    headers = rows[0]
    data = rows[1:]
    fields: list[dict] = []
    for i, h in enumerate(headers):
        if _is_skip_header(h):
            continue
        section, question = _parse_section_question(h)
        vals = _unique_vals(data, i)
        opts = _options_from_vals(vals)

        # skill grids → likert radio
        if "[" in h and "Habilidades" in h:
            valset = {_norm(v) for v in vals}
            if {"logrado", "en proceso", "requiere apoyo"} & valset:
                opts = LOGRADO_3
            else:
                opts = LIKERT_3
            field_type = "radio"
        elif opts and len(opts) <= 2 and {_norm(o["value"]) for o in opts} <= {"si", "no", "sí"}:
            opts = SI_NO
            field_type = "radio"
        elif opts and 2 <= len(opts) <= 8:
            field_type = "radio" if all(len(o["value"]) < 90 for o in opts) else "select"
        elif opts and len(opts) <= 12:
            field_type = "select"
        else:
            opts = []
            # open text
            maxlen = max((len(v) for v in vals), default=0)
            field_type = "textarea" if maxlen > 80 or "recomend" in _norm(question) else "text"

        fields.append(
            {
                "id": _slug(question or h, len(fields) + 1),
                "question": question,
                "section": section,
                "fieldType": field_type,
                "options": opts or [],
                "required": False,
            }
        )
    return fields


def first_course_id(db, school_id: int) -> int | None:
    return db.execute(
        text("SELECT id FROM courses WHERE school_id = :s ORDER BY id LIMIT 1"),
        {"s": school_id},
    ).scalar()


def main() -> None:
    os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL
    eng = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    db = sessionmaker(bind=eng)()

    created = []
    skipped = []
    for stem, (name, respondent, school_ids) in FORM_MAP.items():
        path = CSV_DIR / f"{stem}.csv"
        if not path.exists():
            print("MISSING csv", path)
            continue
        fields = build_fields(path)
        print(f"\n=== {name} === fields={len(fields)} respondent={respondent}")
        for f in fields[:5]:
            print(" ", f["section"] or "-", "|", f["question"][:70], "|", f["fieldType"])
        if len(fields) > 5:
            print(f"  ... +{len(fields)-5} more")
        if not fields:
            print("  SKIP empty fields")
            continue

        for school_id in school_ids:
            exists = (
                db.query(DynamicFormModel)
                .filter(
                    DynamicFormModel.school_id == school_id,
                    DynamicFormModel.period_year == PERIOD_YEAR,
                    DynamicFormModel.name == name,
                    DynamicFormModel.deleted_date.is_(None),
                )
                .first()
            )
            if exists:
                skipped.append((school_id, name, exists.id))
                print(f"  school={school_id} already id={exists.id}")
                continue
            course_id = first_course_id(db, school_id)
            if not course_id:
                print(f"  school={school_id} sin curso")
                continue
            res = DynamicFormClass(db).store(
                {
                    "name": name,
                    "description": (
                        "Importado desde cabeceras Google Forms (sin datos personales; "
                        "identidad del estudiante desde PIE360)."
                    ),
                    "fields": fields,
                    "periodYear": PERIOD_YEAR,
                    "courseId": int(course_id),
                    "respondentTypeId": respondent,
                },
                school_id=school_id,
            )
            print(f"  school={school_id} course={course_id} ->", res)
            if res.get("status") == "success":
                created.append({"school_id": school_id, "name": name, "id": res.get("id"), "fields": len(fields)})

    out = ROOT / "scripts" / "output" / "cuestionarios" / "forms_created.json"
    out.write_text(
        json.dumps({"created": created, "skipped": skipped}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nCREATED {len(created)} SKIPPED {len(skipped)} saved {out}")
    db.close()


if __name__ == "__main__":
    main()
