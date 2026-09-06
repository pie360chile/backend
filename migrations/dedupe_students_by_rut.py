"""Soft-delete estudiantes duplicados (mismo colegio + mismo RUT normalizado).

Conserva el registro con más carpetas / datos personales; normaliza el RUT
del que queda a formato 12345678-9.

Run from backend/:
  python migrations/dedupe_students_by_rut.py
  python migrations/dedupe_students_by_rut.py --dry-run
  python migrations/dedupe_students_by_rut.py --canon-only
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from sqlalchemy import text

from app.backend.classes.student_class import _format_rut_display, _normalize_rut
from app.backend.db.database import SessionLocal


def _norm_sql_expr(col: str) -> str:
    return (
        f"REPLACE(REPLACE(REPLACE(LOWER(TRIM(IFNULL({col}, ''))), '.', ''), '-', ''), ' ', '')"
    )


def _canonicalize_dotted(db, now: datetime) -> int:
    """Solo filas con puntos u otros formatos no canónicos; updates en lote."""
    rows = db.execute(
        text(
            """
            SELECT id, identification_number
            FROM students
            WHERE deleted_status_id = 0
              AND identification_number IS NOT NULL
              AND TRIM(identification_number) <> ''
              AND (
                identification_number LIKE '%.%'
                OR identification_number LIKE '% %'
                OR identification_number NOT LIKE '%-%'
              )
            """
        )
    ).mappings().all()
    updates: list[dict] = []
    for r in rows:
        canon = _format_rut_display(r["identification_number"] or "")
        if not canon or (r["identification_number"] or "").strip() == canon:
            continue
        updates.append({"id": int(r["id"]), "canon": canon, "now": now})

    for i in range(0, len(updates), 100):
        chunk = updates[i : i + 100]
        for u in chunk:
            db.execute(
                text(
                    """
                    UPDATE students
                    SET identification_number = :canon, updated_date = :now
                    WHERE id = :id
                    """
                ),
                u,
            )
            db.execute(
                text(
                    """
                    UPDATE student_personal_data
                    SET identification_number = :canon, updated_date = :now
                    WHERE student_id = :id
                    """
                ),
                u,
            )
        db.commit()
        print(f"canon progress {min(i + 100, len(updates))}/{len(updates)}", flush=True)
    return len(updates)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--canon-only", action="store_true", help="Solo normalizar formato RUT")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        now = datetime.now()

        if args.canon_only:
            if args.dry_run:
                n = db.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM students
                        WHERE deleted_status_id = 0
                          AND identification_number LIKE '%.%'
                        """
                    )
                ).scalar()
                print(f"dry-run: would_canon_approx={n}", flush=True)
                return
            n = _canonicalize_dotted(db, now)
            print(f"applied: canon_extra={n}", flush=True)
            return

        print("loading active students…", flush=True)
        rows = db.execute(
            text(
                """
                SELECT
                  s.id,
                  s.school_id,
                  s.identification_number,
                  s.period_year,
                  COALESCE(f.cnt, 0) AS folder_count,
                  CASE
                    WHEN TRIM(IFNULL(p.names, '')) <> ''
                      OR TRIM(IFNULL(p.father_lastname, '')) <> ''
                      OR TRIM(IFNULL(p.mother_lastname, '')) <> ''
                    THEN 1 ELSE 0
                  END AS has_name
                FROM students s
                LEFT JOIN student_personal_data p ON p.student_id = s.id
                LEFT JOIN (
                  SELECT student_id, COUNT(*) AS cnt
                  FROM folders
                  GROUP BY student_id
                ) f ON f.student_id = s.id
                WHERE s.deleted_status_id = 0
                  AND s.identification_number IS NOT NULL
                  AND TRIM(s.identification_number) <> ''
                """
            )
        ).mappings().all()

        groups: dict[tuple, list] = defaultdict(list)
        for r in rows:
            key = _normalize_rut(r["identification_number"])
            if not key:
                continue
            groups[(int(r["school_id"] or 0), key)].append(r)

        dup_groups = {k: v for k, v in groups.items() if len(v) > 1}
        print(f"active_students={len(rows)} duplicate_groups={len(dup_groups)}", flush=True)

        soft_deleted_ids: list[int] = []
        keep_canon: list[tuple[int, str]] = []

        for (school_id, rut_norm), members in sorted(
            dup_groups.items(), key=lambda x: (-len(x[1]), x[0][0])
        ):
            ranked = sorted(
                members,
                key=lambda m: (int(m["folder_count"]), int(m["has_name"]), -int(m["id"])),
                reverse=True,
            )
            keeper = ranked[0]
            losers = ranked[1:]
            soft_deleted_ids.extend(int(m["id"]) for m in losers)
            canon = _format_rut_display(keeper["identification_number"] or rut_norm)
            keep_canon.append((int(keeper["id"]), canon))
            print(
                f"school={school_id} rut={rut_norm} keep_id={keeper['id']} "
                f"delete_ids={[m['id'] for m in losers]}",
                flush=True,
            )

        if args.dry_run:
            print(f"dry-run: soft_deleted={len(soft_deleted_ids)}", flush=True)
            return

        if soft_deleted_ids:
            for i in range(0, len(soft_deleted_ids), 200):
                chunk = soft_deleted_ids[i : i + 200]
                placeholders = ", ".join(str(int(x)) for x in chunk)
                db.execute(
                    text(
                        f"""
                        UPDATE students
                        SET deleted_status_id = 1, updated_date = :now
                        WHERE id IN ({placeholders}) AND deleted_status_id = 0
                        """
                    ),
                    {"now": now},
                )
            db.commit()

        for sid, canon in keep_canon:
            db.execute(
                text(
                    """
                    UPDATE students
                    SET identification_number = :canon, updated_date = :now
                    WHERE id = :id
                    """
                ),
                {"canon": canon, "now": now, "id": sid},
            )
            db.execute(
                text(
                    """
                    UPDATE student_personal_data
                    SET identification_number = :canon, updated_date = :now
                    WHERE student_id = :id
                    """
                ),
                {"canon": canon, "now": now, "id": sid},
            )
        if keep_canon:
            db.commit()

        print("canonicalizing dotted RUT formats…", flush=True)
        canon_extra = _canonicalize_dotted(db, now)

        left = db.execute(
            text(
                f"""
                SELECT COUNT(*) AS c FROM (
                  SELECT school_id, {_norm_sql_expr('identification_number')} AS rut_norm
                  FROM students
                  WHERE deleted_status_id = 0
                    AND identification_number IS NOT NULL
                    AND TRIM(identification_number) <> ''
                  GROUP BY school_id, {_norm_sql_expr('identification_number')}
                  HAVING COUNT(*) > 1
                ) t
                """
            )
        ).scalar()
        print(
            f"applied: soft_deleted={len(soft_deleted_ids)} "
            f"keepers={len(keep_canon)} canon_extra={canon_extra} "
            f"remaining_duplicate_groups={left}",
            flush=True,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
