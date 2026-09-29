"""Asigna a Leslie (user_id=5) todos los roles excepto Super Administrador.

Run from backend/:
  python migrations/assign_leslie_all_roles_except_superadmin.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from sqlalchemy import text

from app.backend.db.database import SessionLocal

USER_ID = 5
PERIOD_YEAR = 2026
SUPERADMIN_ROL_ID = 1


def main() -> None:
    db = SessionLocal()
    now = datetime.now()
    try:
        roles = db.execute(
            text(
                """
                SELECT id, rol, school_id
                FROM rols
                WHERE (deleted_status_id = 0 OR deleted_status_id IS NULL)
                  AND id <> :super_id
                ORDER BY school_id, id
                """
            ),
            {"super_id": SUPERADMIN_ROL_ID},
        ).mappings().all()

        target_ids = [int(r["id"]) for r in roles]
        print(f"target_roles={len(target_ids)} {[ (r['id'], r['rol'], r['school_id']) for r in roles ]}")

        existing = db.execute(
            text("SELECT id, rol_id, deleted_status_id FROM users_rols WHERE user_id = :uid"),
            {"uid": USER_ID},
        ).mappings().all()
        by_rol = {int(r["rol_id"]): r for r in existing}

        activated = 0
        inserted = 0
        for rid in target_ids:
            row = by_rol.get(rid)
            if row is None:
                db.execute(
                    text(
                        """
                        INSERT INTO users_rols
                          (user_id, rol_id, deleted_status_id, period_year, added_date, updated_date)
                        VALUES
                          (:uid, :rid, 0, :py, :now, :now)
                        """
                    ),
                    {"uid": USER_ID, "rid": rid, "py": PERIOD_YEAR, "now": now},
                )
                inserted += 1
                print(f"INSERT rol_id={rid}")
            else:
                deleted = row["deleted_status_id"]
                if deleted is not None and int(deleted) != 0:
                    db.execute(
                        text(
                            """
                            UPDATE users_rols
                            SET deleted_status_id = 0,
                                period_year = :py,
                                updated_date = :now
                            WHERE id = :id
                            """
                        ),
                        {"py": PERIOD_YEAR, "now": now, "id": int(row["id"])},
                    )
                    activated += 1
                    print(f"REACTIVATE id={row['id']} rol_id={rid}")
                else:
                    print(f"KEEP rol_id={rid}")

        # Soft-delete Superadmin if present
        db.execute(
            text(
                """
                UPDATE users_rols
                SET deleted_status_id = 1, updated_date = :now
                WHERE user_id = :uid AND rol_id = :super_id
                  AND (deleted_status_id = 0 OR deleted_status_id IS NULL)
                """
            ),
            {"now": now, "uid": USER_ID, "super_id": SUPERADMIN_ROL_ID},
        )

        # Soft-delete orphan rol_ids (no longer in rols)
        orphan = db.execute(
            text(
                """
                SELECT ur.id, ur.rol_id
                FROM users_rols ur
                LEFT JOIN rols r ON r.id = ur.rol_id
                WHERE ur.user_id = :uid
                  AND (ur.deleted_status_id = 0 OR ur.deleted_status_id IS NULL)
                  AND r.id IS NULL
                """
            ),
            {"uid": USER_ID},
        ).mappings().all()
        for o in orphan:
            db.execute(
                text(
                    """
                    UPDATE users_rols
                    SET deleted_status_id = 1, updated_date = :now
                    WHERE id = :id
                    """
                ),
                {"now": now, "id": int(o["id"])},
            )
            print(f"SOFT-DELETE orphan users_rols.id={o['id']} rol_id={o['rol_id']}")

        db.commit()

        active = db.execute(
            text(
                """
                SELECT ur.rol_id, r.rol, r.school_id
                FROM users_rols ur
                JOIN rols r ON r.id = ur.rol_id
                WHERE ur.user_id = :uid
                  AND (ur.deleted_status_id = 0 OR ur.deleted_status_id IS NULL)
                ORDER BY r.school_id, r.rol
                """
            ),
            {"uid": USER_ID},
        ).mappings().all()
        print(f"done inserted={inserted} activated={activated} active_now={len(active)}")
        for a in active:
            print(dict(a))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
