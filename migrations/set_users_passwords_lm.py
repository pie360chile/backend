"""Actualiza claves de usuarios por RUT.

Run from backend/:
  python migrations/set_users_passwords_lm.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from sqlalchemy import text

from app.backend.auth.auth_user import generate_bcrypt_hash
from app.backend.db.database import SessionLocal

# rut_norm (sin puntos/guiones), password, etiqueta
USERS = [
    ("131348487", "lm_n0000", "Ninoska Irene Ramírez Garrido"),
    ("132521719", "lm_c0001", "Carolina Soledad Flores Aedo"),
    ("168491085", "lm_g0002", "Gwendolyn Verónica Tapia Tapia"),
    ("195825815", "lm_l0003", "Leslie Luisa Michaelle Cabrera Valencia"),
]


def norm(raw: str) -> str:
    return "".join(c for c in str(raw).upper() if c.isalnum())


def main() -> None:
    db = SessionLocal()
    try:
        rows = db.execute(
            text(
                """
                SELECT id, rut, full_name
                FROM users
                WHERE deleted_status_id = 0 OR deleted_status_id IS NULL
                """
            )
        ).mappings().all()
        by_norm: dict[str, list] = {}
        for r in rows:
            by_norm.setdefault(norm(r["rut"] or ""), []).append(r)

        updated = 0
        for rut_key, password, label in USERS:
            matches = by_norm.get(rut_key) or []
            print(f"{label} ({rut_key}): matches={len(matches)}")
            for m in matches:
                print(f"  id={m['id']} rut={m['rut']} name={m['full_name']}")
            if len(matches) != 1:
                print("  SKIP: expected exactly 1 user")
                continue
            m = matches[0]
            db.execute(
                text("UPDATE users SET hashed_password = :h WHERE id = :id"),
                {"h": generate_bcrypt_hash(password), "id": int(m["id"])},
            )
            print(f"  OK password set")
            updated += 1
        db.commit()
        print(f"done updated={updated}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
