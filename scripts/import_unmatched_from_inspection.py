"""Cruza import_unmatched.csv con Inspection (todos los colegios) y guarda
solo alumnos que existen en Inspection, no están en PIE360 (sin duplicar RUT).

Uso:
  python scripts/import_unmatched_from_inspection.py           # dry-run
  python scripts/import_unmatched_from_inspection.py --apply   # guardar
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.backend.classes.inspection_api_client import InspectionApiClient
from app.backend.classes.student_class import (
    StudentClass,
    _extract_inspection_students_rows,
    _identification_key_for_dedupe,
    _inspection_int,
)
from app.backend.db.database import SessionLocal
from app.backend.db.models import CourseModel, SchoolModel, StudentModel, StudentPersonalInfoModel

UNMATCHED_CSV = ROOT / "scripts" / "output" / "import_unmatched.csv"
OUT_CSV = ROOT / "scripts" / "output" / "import_unmatched_inspection_result.csv"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", s)).strip()


def toks(s: str) -> list[str]:
    stop = {
        "de",
        "del",
        "la",
        "las",
        "los",
        "y",
        "b",
        "a",
        "medio",
        "basica",
        "pk",
        "k",
        "informe",
        "familia",
        "b1",
        "b2",
        "bsf",
        "tda",
        "tea",
        "discapacidad",
    }
    return [t for t in norm(s).split() if t and t not in stop and not t.isdigit()]


def score_name(ft: list[str], st: list[str]) -> int:
    if not ft or not st:
        return 0
    if ft[0] not in st:
        return 0
    if set(ft).issubset(set(st)):
        return 100 if ft == st else 90
    if len(ft) >= 2 and ft[0] in st and ft[-1] in st:
        return 80
    return 0


def clean_extracted_name(raw: str) -> str:
    """Quita curso/prefijos del nombre extraído del CSV unmatched."""
    s = (raw or "").strip()
    s = re.sub(r"\.(docx|pdf|doc)$", "", s, flags=re.I)
    s = re.sub(r"^(?:PK|K)?\s*\d+[°ºo]?\s*[A-Za-zÁÉÍÓÚáéíóú]?\s*", "", s, flags=re.I)
    s = re.sub(r"\s+B\d+\s*$", "", s, flags=re.I)
    s = re.sub(r"\s+BSF\s*$", "", s, flags=re.I)
    s = re.sub(r"\s*[-–]\s*(TDA|TEA|DISCAPACIDAD).*$", "", s, flags=re.I)
    return s.strip(" -_")


def load_unmatched() -> list[dict]:
    rows = []
    with UNMATCHED_CSV.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            school_id = int(str(row.get("school_id") or "0").strip() or 0)
            nombre = clean_extracted_name(row.get("nombre_extraido") or "")
            if school_id < 1 or not nombre:
                continue
            rows.append(
                {
                    "school_id": school_id,
                    "liceo": row.get("liceo") or "",
                    "nombre_extraido": nombre,
                    "archivo_drive": row.get("archivo_drive") or "",
                    "drive_file_id": row.get("drive_file_id") or "",
                    "tipo_informe": row.get("tipo_informe") or "",
                    "document_id": row.get("document_id") or "",
                    "toks": toks(nombre),
                }
            )
    return rows


def full_name_from_inspection(row: dict) -> str:
    return " ".join(
        filter(
            None,
            [
                str(row.get("nombres") or "").strip(),
                str(row.get("paterno") or "").strip(),
                str(row.get("materno") or "").strip(),
            ],
        )
    )


def existing_ruts(db, school_ids: list[int]) -> set[str]:
    keys: set[str] = set()
    q = (
        db.query(StudentModel.identification_number)
        .filter(
            StudentModel.deleted_status_id == 0,
            StudentModel.school_id.in_(school_ids),
        )
        .all()
    )
    for (rut,) in q:
        if rut:
            keys.add(_identification_key_for_dedupe(str(rut)))
    # También personal_info por si el RUT solo está allí
    personal = (
        db.query(StudentPersonalInfoModel.identification_number, StudentModel.school_id)
        .join(StudentModel, StudentModel.id == StudentPersonalInfoModel.student_id)
        .filter(
            StudentModel.deleted_status_id == 0,
            StudentModel.school_id.in_(school_ids),
        )
        .all()
    )
    for rut, _sid in personal:
        if rut:
            keys.add(_identification_key_for_dedupe(str(rut)))
    return keys


def find_unique_inspection_match(
    unmatched: dict, insp_rows: list[dict]
) -> tuple[dict | None, str]:
    """Devuelve (fila_inspection, motivo) solo si hay un candidato claro."""
    ft = unmatched["toks"]
    scored: list[tuple[int, dict]] = []
    for row in insp_rows:
        st = toks(full_name_from_inspection(row))
        sc = score_name(ft, st)
        if sc >= 90:
            scored.append((sc, row))
    if not scored:
        return None, "sin_match_inspection"
    scored.sort(key=lambda x: (-x[0], full_name_from_inspection(x[1])))
    best_score = scored[0][0]
    top = [r for sc, r in scored if sc == best_score]
    if len(top) != 1:
        names = "; ".join(full_name_from_inspection(r) for r in top[:5])
        return None, f"ambiguo_inspection:{names}"
    return top[0], f"match_{best_score}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Guardar estudiantes faltantes")
    parser.add_argument("--anio", type=int, default=datetime.now().year)
    parser.add_argument(
        "--customer-id",
        type=int,
        default=2,
        help="Customer cuyos colegios se consultan",
    )
    args = parser.parse_args()

    if not UNMATCHED_CSV.is_file():
        print(f"No existe {UNMATCHED_CSV}")
        return 1

    unmatched = load_unmatched()
    by_school: dict[int, list[dict]] = defaultdict(list)
    for u in unmatched:
        by_school[u["school_id"]].append(u)

    db = SessionLocal()
    client = InspectionApiClient()
    if not client.is_configured():
        print("Inspection API no configurada (INSPECTION_API_USERNAME / PASSWORD)")
        return 1

    schools = (
        db.query(SchoolModel)
        .filter(
            SchoolModel.customer_id == int(args.customer_id),
            SchoolModel.deleted_status_id == 0,
        )
        .order_by(SchoolModel.id.asc())
        .all()
    )
    school_ids = [int(s.id) for s in schools]
    print(f"Colegios customer {args.customer_id}: {school_ids}")
    print(f"Unmatched CSV: {len(unmatched)} filas | dry-run={not args.apply}")

    already = existing_ruts(db, school_ids)
    student_svc = StudentClass(db)
    results: list[dict] = []
    saved = 0
    would_save = 0
    skipped_exists = 0
    no_match = 0
    ambiguous = 0
    errors = 0

    # Dedup global por RUT durante esta corrida
    seen_this_run: set[str] = set()

    for school in schools:
        sid = int(school.id)
        remote = client.fetch_students_list(colegio_id=sid, anio=int(args.anio))
        if not remote.get("ok"):
            print(f"[school {sid}] Inspection error: {remote.get('message')}")
            for u in by_school.get(sid, []):
                results.append({**u, "status": "inspection_error", "message": remote.get("message")})
                errors += 1
            continue

        insp_rows = _extract_inspection_students_rows(remote)
        print(f"[school {sid}] Inspection alumnos: {len(insp_rows)} | unmatched CSV: {len(by_school.get(sid, []))}")

        # También cruzar unmatched de ESTE colegio
        for u in by_school.get(sid, []):
            match, reason = find_unique_inspection_match(u, insp_rows)
            if not match:
                status = "ambiguous" if reason.startswith("ambiguo") else "no_match"
                if status == "ambiguous":
                    ambiguous += 1
                else:
                    no_match += 1
                results.append(
                    {
                        **u,
                        "status": status,
                        "message": reason,
                        "rut": "",
                        "inspection_name": "",
                    }
                )
                continue

            rut_raw = (match.get("rut") or match.get("identification_number") or "").strip()
            insp_name = full_name_from_inspection(match)
            if not rut_raw:
                results.append(
                    {
                        **u,
                        "status": "error",
                        "message": "Inspection sin RUT",
                        "rut": "",
                        "inspection_name": insp_name,
                    }
                )
                errors += 1
                continue

            id_key = _identification_key_for_dedupe(rut_raw)
            if id_key in already or id_key in seen_this_run:
                skipped_exists += 1
                results.append(
                    {
                        **u,
                        "status": "already_exists",
                        "message": "Ya existe en PIE360 (no se repite)",
                        "rut": rut_raw,
                        "inspection_name": insp_name,
                    }
                )
                continue

            course_remote = _inspection_int(
                match.get("curso_id") if match.get("curso_id") is not None else match.get("cursoId")
            )
            if course_remote is None:
                results.append(
                    {
                        **u,
                        "status": "error",
                        "message": "Inspection sin curso_id",
                        "rut": rut_raw,
                        "inspection_name": insp_name,
                    }
                )
                errors += 1
                continue

            course_row = (
                db.query(CourseModel)
                .filter(
                    CourseModel.id == course_remote,
                    CourseModel.school_id == sid,
                    CourseModel.deleted_status_id == 0,
                )
                .first()
            )
            if not course_row:
                results.append(
                    {
                        **u,
                        "status": "error",
                        "message": f"Curso {course_remote} no existe en colegio {sid}; importa cursos primero",
                        "rut": rut_raw,
                        "inspection_name": insp_name,
                    }
                )
                errors += 1
                continue

            py_raw = match.get("anio")
            period_year = _inspection_int(py_raw) if py_raw not in (None, "") else int(args.anio)
            if period_year is None:
                period_year = int(args.anio)

            payload = {
                "school_id": sid,
                "identification_number": rut_raw,
                "period_year": period_year,
                "course_id": course_remote,
                "names": str(match.get("nombres") or "").strip() or "—",
                "father_lastname": str(match.get("paterno") or "").strip(),
                "mother_lastname": str(match.get("materno") or "").strip(),
                "born_date": (str(match.get("fecha_nacimiento")).strip()[:10] if match.get("fecha_nacimiento") else None),
                "email": (str(match.get("email")).strip() if match.get("email") else None) or None,
                "phone": (str(match.get("telefono")).strip() if match.get("telefono") else None) or None,
                "address": (str(match.get("direccion")).strip() if match.get("direccion") else None) or None,
                "nationality_id": _inspection_int(match.get("nacionalidad_id")),
                "gender_id": _inspection_int(match.get("sexo")),
                "commune_id": _inspection_int(match.get("comuna_id")),
            }

            if not args.apply:
                would_save += 1
                seen_this_run.add(id_key)
                results.append(
                    {
                        **u,
                        "status": "would_save",
                        "message": reason,
                        "rut": rut_raw,
                        "inspection_name": insp_name,
                        "course_id": course_remote,
                    }
                )
                continue

            result = student_svc.store(payload)
            if isinstance(result, dict) and result.get("status") == "success":
                new_id = result.get("student_id")
                if new_id is not None:
                    try:
                        student_svc._provision_inspection_import_extras(
                            int(new_id),
                            int(sid),
                            int(course_remote),
                            int(period_year),
                            payload,
                        )
                    except Exception as pe:
                        print(f"  warn provisioning {rut_raw}: {pe}")
                saved += 1
                already.add(id_key)
                seen_this_run.add(id_key)
                results.append(
                    {
                        **u,
                        "status": "saved",
                        "message": reason,
                        "rut": rut_raw,
                        "inspection_name": insp_name,
                        "student_id": new_id,
                        "course_id": course_remote,
                    }
                )
            else:
                msg = (result or {}).get("message") or "Error al guardar"
                if isinstance(msg, str) and "Ya existe un estudiante" in msg:
                    skipped_exists += 1
                    already.add(id_key)
                    results.append(
                        {
                            **u,
                            "status": "already_exists",
                            "message": msg,
                            "rut": rut_raw,
                            "inspection_name": insp_name,
                        }
                    )
                else:
                    errors += 1
                    results.append(
                        {
                            **u,
                            "status": "error",
                            "message": str(msg),
                            "rut": rut_raw,
                            "inspection_name": insp_name,
                        }
                    )

    # Escribir CSV resultado
    fields = [
        "status",
        "message",
        "school_id",
        "liceo",
        "nombre_extraido",
        "inspection_name",
        "rut",
        "archivo_drive",
        "drive_file_id",
        "tipo_informe",
        "document_id",
        "student_id",
        "course_id",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow(r)

    print("---")
    print(f"would_save={would_save} saved={saved} already_exists={skipped_exists}")
    print(f"no_match={no_match} ambiguous={ambiguous} errors={errors}")
    print(f"Resultado: {OUT_CSV}")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
