"""
Carga one-off: customer Liceo Mixto San Felipe, escuela id 20, roles 3-5 y usuarios @pie360.cl.

Ejecutar desde la raíz del backend:
  py scripts/seed_liceo_mixto_san_felipe_users.py

Usa credenciales de app/backend/db/database.py (misma BD que el API).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

# Raíz del proyecto backend en sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pymysql  # noqa: E402
from app.backend.db.database import SQLALCHEMY_DATABASE_URI  # noqa: E402
from app.backend.auth.auth_user import generate_bcrypt_hash  # noqa: E402

# --- Config ---
SCHOOL_ID = 20
SCHOOL_NAME = "Liceo Mixto San Felipe"
CUSTOMER_COMPANY = "Liceo Mixto San Felipe"

# Permisos copiados del rol Administrador (id 2) en producción
ADMIN_PERM_IDS = [1, 2, 3, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 40, 41, 43, 44, 56]

# (full_name, rut_formateado, password, [(email_suffix_key, rol_id), ...])
# emails: lm{key}@pie360.cl — key viene del listado
PEOPLE: list[tuple[str, str, str, list[tuple[str, int]]]] = [
    (
        "Ninoska Irene Ramírez Garrido",
        "13.134.848-7",
        "pie360_lm_0000",
        [
            ("lmramirez_sad@pie360.cl", 1),
            ("lmramirez_ad@pie360.cl", 2),
            ("lmramirez_ev@pie360.cl", 3),
            ("lmramirez_co@pie360.cl", 4),
            ("lmramirez_pr@pie360.cl", 5),
        ],
    ),
    (
        "Carolina Soledad Flores Aedo",
        "13.252.171-9",
        "pie360_lm_0001",
        [
            ("lmflores_sad@pie360.cl", 1),
            ("lmflores_ad@pie360.cl", 2),
            ("lmflores_ev@pie360.cl", 3),
            ("lmflores_co@pie360.cl", 4),
            ("lmflores_pr@pie360.cl", 5),
        ],
    ),
    (
        "Gwendolyn Verónica Tapia Tapia",
        "16.849.108-5",
        "pie360_lm_0002",
        [
            ("lmtapia_ad@pie360.cl", 2),
            ("lmtapia_ev@pie360.cl", 3),
            ("lmtapia_co@pie360.cl", 4),
            ("lmtapia_pr@pie360.cl", 5),
        ],
    ),
    (
        "Leslie Luisa Michaelle Cabrera Valencia",
        "19.582.581-5",
        "pie360_lm_0003",
        [
            ("lmcabrera_ev@pie360.cl", 3),
        ],
    ),
]

def _parse_mysql_uri(uri: str) -> dict:
    # mysql+pymysql://user:pass@host:port/db
    rest = uri.split("mysql+pymysql://", 1)[1]
    auth, hostpart = rest.rsplit("@", 1)
    user, password = auth.split(":", 1)
    host_db = hostpart.split("/", 1)
    host_port = host_db[0].split(":")
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 3306
    database = host_db[1].split("?")[0]
    return {"host": host, "port": port, "user": user, "password": password, "database": database}


def _split_name(full: str) -> tuple[str, str]:
    parts = full.strip().split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return full, ""


def main() -> None:
    cfg = _parse_mysql_uri(SQLALCHEMY_DATABASE_URI)
    conn = pymysql.connect(
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        **cfg,
    )
    now = datetime.now()
    pwd_hashes: dict[str, str] = {}
    for _, _, pwd, _ in PEOPLE:
        if pwd not in pwd_hashes:
            pwd_hashes[pwd] = generate_bcrypt_hash(pwd)

    try:
        with conn.cursor() as cur:
            # 1) Customer
            cur.execute(
                "SELECT id FROM customers WHERE company_name = %s AND deleted_status_id = 0 LIMIT 1",
                (CUSTOMER_COMPANY,),
            )
            row = cur.fetchone()
            if row:
                customer_id = row["id"]
                print(f"Customer existente id={customer_id} ({CUSTOMER_COMPANY})")
            else:
                cur.execute(
                    """
                    INSERT INTO customers (
                        country_id, region_id, commune_id, package_id, bill_or_ticket_id,
                        deleted_status_id, identification_number, names, lastnames, address,
                        company_name, email, phone, license_time, added_date, updated_date
                    ) VALUES (
                        1, 1, 1, NULL, 0,
                        0, %s, %s, %s, %s,
                        %s, %s, %s, NULL, %s, %s
                    )
                    """,
                    (
                        "96.000.000-0",
                        "Liceo Mixto",
                        "San Felipe",
                        "San Felipe, Chile",
                        CUSTOMER_COMPANY,
                        "contacto@pie360.cl",
                        "+56900000000",
                        now,
                        now,
                    ),
                )
                customer_id = cur.lastrowid
                print(f"Customer creado id={customer_id}")

            # 2) Escuela
            cur.execute(
                "SELECT id, school_name, customer_id, deleted_status_id FROM schools WHERE id = %s",
                (SCHOOL_ID,),
            )
            sch = cur.fetchone()
            if not sch:
                raise SystemExit(f"No existe school id={SCHOOL_ID}")
            print(f"Escuela: {sch}")
            cur.execute(
                "UPDATE schools SET customer_id = %s, updated_date = %s WHERE id = %s",
                (customer_id, now, SCHOOL_ID),
            )

            # 3) Roles 3,4,5 + permisos (si faltan)
            for rid, label in [(3, "Evaluador"), (4, "Coordinador"), (5, "Profesional")]:
                cur.execute(
                    "SELECT id FROM rols WHERE deleted_status_id = 0 AND rol = %s LIMIT 1",
                    (label,),
                )
                ex = cur.fetchone()
                if ex:
                    print(f"Rol ya existe: {label} id={ex['id']}")
                    continue
                cur.execute(
                    """
                    INSERT INTO rols (customer_id, school_id, deleted_status_id, rol, added_date, updated_date)
                    VALUES (NULL, NULL, 0, %s, %s, %s)
                    """,
                    (label, now, now),
                )
                new_id = cur.lastrowid
                print(f"Rol creado: {label} id={new_id}")
                for pid in ADMIN_PERM_IDS:
                    cur.execute(
                        """
                        INSERT INTO rols_permissions (rol_id, permission_id, added_date, updated_date)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (new_id, pid, now, now),
                    )

            cur.execute(
                "SELECT id, rol FROM rols WHERE deleted_status_id = 0 AND rol IN ('Evaluador','Coordinador','Profesional')"
            )
            for r in cur.fetchall():
                print(f"  Rol en BD: id={r['id']} name={r['rol']}")

            # 4) Usuarios
            for full_name, rut, plain_pwd, accounts in PEOPLE:
                h = pwd_hashes[plain_pwd]
                for email, rol_id in accounts:
                    cur.execute("SELECT id FROM users WHERE email = %s LIMIT 1", (email,))
                    u = cur.fetchone()
                    if u:
                        cur.execute(
                            """
                            UPDATE users SET
                                customer_id = %s, school_id = %s, rol_id = %s,
                                rut = %s, full_name = %s, hashed_password = %s,
                                deleted_status_id = 0, updated_date = %s
                            WHERE id = %s
                            """,
                            (customer_id, SCHOOL_ID, rol_id, rut, full_name, h, now, u["id"]),
                        )
                        print(f"  UPDATE user id={u['id']} {email} rol={rol_id}")
                    else:
                        cur.execute(
                            """
                            INSERT INTO users (
                                customer_id, school_id, rol_id, deleted_status_id,
                                rut, full_name, email, phone, hashed_password, added_date, updated_date
                            ) VALUES (%s, %s, %s, 0, %s, %s, %s, NULL, %s, %s, %s)
                            """,
                            (customer_id, SCHOOL_ID, rol_id, rut, full_name, email, h, now, now),
                        )
                        print(f"  INSERT user {email} rol={rol_id}")

            # 5) Profesionales (mismo RUT por persona, escuela 20) — para login Evaluador/Profesional
            seen_ruts: set[str] = set()
            for full_name, rut, _, accounts in PEOPLE:
                needs_prof = any(rid in (3, 5) for _, rid in accounts)
                if not needs_prof:
                    continue
                if rut in seen_ruts:
                    continue
                seen_ruts.add(rut)
                names, lastnames = _split_name(full_name)
                cur.execute(
                    """
                    SELECT id FROM professionals
                    WHERE school_id = %s AND identification_number = %s
                    LIMIT 1
                    """,
                    (SCHOOL_ID, rut),
                )
                pr = cur.fetchone()
                if pr:
                    cur.execute(
                        """
                        UPDATE professionals SET names = %s, lastnames = %s, email = %s, updated_date = %s
                        WHERE id = %s
                        """,
                        (names, lastnames, None, now, pr["id"]),
                    )
                    print(f"  UPDATE professional id={pr['id']} rut={rut}")
                else:
                    cur.execute(
                        """
                        INSERT INTO professionals (
                            school_id, rol_id, career_type_id, identification_number,
                            names, lastnames, email, birth_date, address, phone,
                            period_year, added_date, updated_date
                        ) VALUES (%s, NULL, NULL, %s, %s, %s, NULL, NULL, NULL, NULL, NULL, %s, %s)
                        """,
                        (SCHOOL_ID, rut, names, lastnames, now, now),
                    )
                    print(f"  INSERT professional rut={rut}")

        conn.commit()
        print("OK — commit realizado.")
    except Exception as e:
        conn.rollback()
        print("ERROR:", e)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
