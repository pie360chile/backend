"""Pipeline Inspection: catálogos → enseñanzas → cursos → alumnos faltantes.

No duplica RUT. Si falta el curso, primero importa enseñanzas/cursos.

Uso:
  python scripts/import_missing_inspection_students.py --anio 2026 --customer-id 2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.backend.classes.commune_class import CommuneClass
from app.backend.classes.course_class import CourseClass
from app.backend.classes.inspection_api_client import InspectionApiClient
from app.backend.classes.nationalities_class import NationalitiesClass
from app.backend.classes.province_class import ProvinceClass
from app.backend.classes.region_class import RegionClass
from app.backend.classes.student_class import StudentClass
from app.backend.classes.teaching_class import TeachingClass
from app.backend.db.database import SessionLocal
from app.backend.db.models import SchoolModel

OUT = ROOT / "scripts" / "output" / "import_missing_inspection_result.txt"


def _summarize(label: str, result: dict) -> str:
    if not isinstance(result, dict):
        return f"{label}: {result}"
    if result.get("status") == "error":
        return f"{label}: ERROR {result.get('message')}"
    return (
        f"{label}: imported={result.get('imported', 0)} "
        f"skipped={result.get('skipped', 0)} "
        f"errors={len(result.get('errors') or [])}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anio", type=int, default=2026)
    parser.add_argument("--customer-id", type=int, default=2)
    parser.add_argument("--skip-catalogs", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    client = InspectionApiClient()
    if not client.is_configured():
        print("Inspection API no configurada")
        return 1

    log_lines: list[str] = []

    # --- Catálogos globales (una vez) ---
    if not args.skip_catalogs:
        print("=== Catálogos Inspection ===")
        catalogs = [
            ("nationalities", client.fetch_nationalities_list, NationalitiesClass),
            ("regions", client.fetch_regions_list, RegionClass),
            ("provinces", client.fetch_provinces_list, ProvinceClass),
            ("communes", client.fetch_communes_list, CommuneClass),
        ]
        for name, fetch_fn, cls in catalogs:
            if not hasattr(client, fetch_fn.__name__ if hasattr(fetch_fn, "__name__") else ""):
                pass
            remote = fetch_fn()
            if not remote.get("ok"):
                msg = f"{name}: ERROR fetch {remote.get('message')}"
                print(msg)
                log_lines.append(msg)
                continue
            result = cls(db).import_from_inspection(remote)
            line = _summarize(name, result)
            print(line)
            log_lines.append(line)

    schools = (
        db.query(SchoolModel)
        .filter(
            SchoolModel.customer_id == int(args.customer_id),
            SchoolModel.deleted_status_id == 0,
        )
        .order_by(SchoolModel.id.asc())
        .all()
    )

    teaching_svc = TeachingClass(db)
    course_svc = CourseClass(db)
    student_svc = StudentClass(db)

    total_imported = 0
    total_skipped = 0
    all_errors: list[dict] = []

    for s in schools:
        sid = int(s.id)
        print(f"\n=== school {sid} {s.school_name} ===")

        # 1) Enseñanzas
        remote_t = client.fetch_teachings_for_active_school(sid)
        if not remote_t.get("ok"):
            msg = f"teachings school {sid}: ERROR {remote_t.get('message')}"
            print(msg)
            log_lines.append(msg)
        else:
            res_t = teaching_svc.import_from_inspection(sid, remote_t)
            line = _summarize(f"teachings school {sid}", res_t)
            print(line)
            log_lines.append(line)

        # 2) Cursos
        remote_c = client.fetch_courses_list(colegio_id=sid, anio=int(args.anio))
        if not remote_c.get("ok"):
            msg = f"courses school {sid}: ERROR {remote_c.get('message')}"
            print(msg)
            log_lines.append(msg)
        else:
            res_c = course_svc.import_from_inspection(sid, remote_c, int(args.anio))
            line = _summarize(f"courses school {sid}", res_c)
            print(line)
            log_lines.append(line)
            for e in (res_c.get("errors") or [])[:10]:
                print(f"   course err: {e}")

        # 3) Alumnos
        remote_s = client.fetch_students_list(colegio_id=sid, anio=int(args.anio))
        if not remote_s.get("ok"):
            msg = remote_s.get("message") or "Inspection students error"
            print(f"students school {sid}: ERROR {msg}")
            all_errors.append({"school_id": sid, "name": f"school:{sid}", "message": msg})
            continue

        result = student_svc.import_from_inspection(sid, remote_s, int(args.anio))
        if result.get("status") == "error":
            msg = result.get("message") or "Import students error"
            print(f"students school {sid}: ERROR {msg}")
            all_errors.append({"school_id": sid, "name": f"school:{sid}", "message": msg})
            continue

        imp = int(result.get("imported") or 0)
        sk = int(result.get("skipped") or 0)
        errs = result.get("errors") or []
        total_imported += imp
        total_skipped += sk
        line = f"students school {sid}: imported={imp} skipped={sk} errors={len(errs)}"
        print(line)
        log_lines.append(line)
        for e in errs[:20]:
            print(f"   - {e.get('name')}: {e.get('message')}")
            all_errors.append({"school_id": sid, **e})
        if len(errs) > 20:
            print(f"   ... +{len(errs) - 20} more")
            for e in errs[20:]:
                all_errors.append({"school_id": sid, **e})

    print("\n=== TOTAL ALUMNOS ===")
    print(f"imported={total_imported}")
    print(f"skipped={total_skipped}")
    print(f"errors={len(all_errors)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        f.write(f"imported={total_imported} skipped={total_skipped} errors={len(all_errors)}\n")
        for line in log_lines:
            f.write(line + "\n")
        for e in all_errors:
            f.write(f"{e}\n")
    print(f"log={OUT}")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
