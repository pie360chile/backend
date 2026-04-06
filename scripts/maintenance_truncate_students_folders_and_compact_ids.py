"""
Mantenimiento de BD (MySQL pie360):

1) Borra todos los registros relacionados con estudiantes y la tabla `folders` (archivos),
   y deja AUTO_INCREMENT en 1 para esas tablas.

2) Compacta los `id` en el resto de tablas con columna `id` (entero): 1..n sin huecos,
   actualizando FKs según INFORMATION_SCHEMA.

Uso (desde la raíz del backend):
  py scripts/maintenance_truncate_students_folders_and_compact_ids.py --dry-run
  py scripts/maintenance_truncate_students_folders_and_compact_ids.py --execute

Requiere la misma URI que app/backend/db/database.py (o variables MYSQL_* abajo).
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# pylint: disable=wrong-import-position
from app.backend.db.database import SQLALCHEMY_DATABASE_URI  # noqa: E402

try:
    import pymysql
except ImportError as e:
    raise SystemExit("Instale pymysql: pip install pymysql") from e


def _parse_mysql_uri(uri: str) -> dict:
    rest = uri.split("mysql+pymysql://", 1)[1]
    auth, hostpart = rest.rsplit("@", 1)
    user, password = auth.split(":", 1)
    host_db = hostpart.split("/", 1)
    host_port = host_db[0].split(":")
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 3306
    database = host_db[1].split("?")[0]
    return {"host": host, "port": port, "user": user, "password": password, "database": database}


def _connect():
    return pymysql.connect(
        **_parse_mysql_uri(SQLALCHEMY_DATABASE_URI),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def _tables_with_column(conn, column: str) -> List[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND COLUMN_NAME = %s
            ORDER BY TABLE_NAME
            """,
            (column,),
        )
        return [r["TABLE_NAME"] for r in cur.fetchall()]


def _fk_incoming(conn) -> List[Dict[str, Any]]:
    """Filas donde otra tabla referencia TABLE_NAME.id (columna REFERENCED_COLUMN_NAME)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND REFERENCED_TABLE_SCHEMA = DATABASE()
              AND REFERENCED_TABLE_NAME IS NOT NULL
            """
        )
        return list(cur.fetchall())


def _integer_id_tables(conn) -> List[str]:
    """Tablas base con columna `id` entera (para compactar)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT C.TABLE_NAME, C.DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS C
            INNER JOIN INFORMATION_SCHEMA.TABLES T
              ON C.TABLE_SCHEMA = T.TABLE_SCHEMA AND C.TABLE_NAME = T.TABLE_NAME
            WHERE C.TABLE_SCHEMA = DATABASE()
              AND C.COLUMN_NAME = 'id'
              AND T.TABLE_TYPE = 'BASE TABLE'
            """
        )
        rows = cur.fetchall()
    out = []
    for r in rows:
        if r["DATA_TYPE"].lower() in ("int", "bigint", "smallint", "mediumint", "integer"):
            out.append(r["TABLE_NAME"])
    return sorted(set(out))


def truncate_students_and_folders(conn, dry_run: bool, truncate_list: Optional[List[str]] = None) -> None:
    tables_truncate = truncate_list or list(
        dict.fromkeys(_tables_with_column(conn, "student_id") + ["students", "folders"])
    )
    print(f"[1] TRUNCATE {len(tables_truncate)} tablas (estudiantes + folders + *_student_id)")
    if dry_run:
        for t in tables_truncate:
            print(f"    DRY RUN TRUNCATE `{t}`")
        return

    with conn.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        for t in tables_truncate:
            cur.execute(f"TRUNCATE TABLE `{t}`")
            print(f"    TRUNCATE `{t}`")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
    conn.commit()

    with conn.cursor() as cur:
        for t in tables_truncate:
            cur.execute(f"ALTER TABLE `{t}` AUTO_INCREMENT = 1")
            print(f"    ALTER `{t}` AUTO_INCREMENT=1")
    conn.commit()


def _build_incoming_map(fk_rows: List[Dict[str, Any]]) -> Dict[str, List[Tuple[str, str]]]:
    """referenced_table -> [(child_table, child_column), ...] solo si referencia columna 'id'."""
    m: Dict[str, List[Tuple[str, str]]] = {}
    for r in fk_rows:
        ref_t = r["REFERENCED_TABLE_NAME"]
        ref_c = r["REFERENCED_COLUMN_NAME"]
        if ref_c != "id":
            continue
        child = r["TABLE_NAME"]
        col = r["COLUMN_NAME"]
        m.setdefault(ref_t, []).append((child, col))
    return m


def compact_table_ids(conn, table: str, dry_run: bool, incoming: Dict[str, List[Tuple[str, str]]]) -> None:
    """
    Compacta id a 1..n sin colisiones PK:
    1) Suma offset grande a id del padre y a las FKs hijas.
    2) Reasigna a 1..n en el padre y en hijos.
    """
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS c FROM `{table}`")
        n = int(cur.fetchone()["c"])
    if n == 0:
        if not dry_run:
            with conn.cursor() as cur:
                cur.execute(f"ALTER TABLE `{table}` AUTO_INCREMENT = 1")
            conn.commit()
        return
    if n == 1:
        with conn.cursor() as cur:
            cur.execute(f"SELECT id FROM `{table}` LIMIT 1")
            only = int(cur.fetchone()["id"])
        if only == 1:
            if not dry_run:
                with conn.cursor() as cur:
                    cur.execute(f"ALTER TABLE `{table}` AUTO_INCREMENT = 2")
                conn.commit()
            return
        if not dry_run:
            children = list({(c, col) for c, col in incoming.get(table, [])})
            offset = only + 1_000_000
            with conn.cursor() as cur:
                cur.execute("SET FOREIGN_KEY_CHECKS=0")
                cur.execute(f"UPDATE `{table}` SET id = id + %s", (offset,))
                for child, col in children:
                    cur.execute(
                        f"UPDATE `{child}` SET `{col}` = `{col}` + %s WHERE `{col}` = %s",
                        (offset, only),
                    )
                cur.execute(f"UPDATE `{table}` SET id = 1 WHERE id = %s", (only + offset,))
                for child, col in children:
                    cur.execute(
                        f"UPDATE `{child}` SET `{col}` = 1 WHERE `{col}` = %s",
                        (only + offset,),
                    )
                cur.execute("SET FOREIGN_KEY_CHECKS=1")
            conn.commit()
            with conn.cursor() as cur:
                cur.execute(f"ALTER TABLE `{table}` AUTO_INCREMENT = 2")
            conn.commit()
        return

    with conn.cursor() as cur:
        cur.execute(f"SELECT id FROM `{table}` ORDER BY id")
        old_ids = [int(r["id"]) for r in cur.fetchall()]
    mapping = {old: i + 1 for i, old in enumerate(old_ids)}
    if all(old == mapping[old] for old in old_ids):
        return

    children = list({(c, col) for c, col in incoming.get(table, [])})
    print(f"  compact `{table}` ({n} rows) -> 1..{n}")

    if dry_run:
        for child, col in children:
            print(f"    DRY bump+remap `{child}`.`{col}`")
        print(f"    DRY bump+remap `{table}`.id")
        return

    offset = max(old_ids) + 1_000_000

    with conn.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        cur.execute(f"UPDATE `{table}` SET id = id + %s", (offset,))
        placeholders = ",".join(["%s"] * len(old_ids))
        for child, col in children:
            cur.execute(
                f"UPDATE `{child}` SET `{col}` = `{col}` + %s WHERE `{col}` IN ({placeholders})",
                (offset, *old_ids),
            )
        for old, new in mapping.items():
            bumped = old + offset
            cur.execute(f"UPDATE `{table}` SET id = %s WHERE id = %s", (new, bumped))
            for child, col in children:
                cur.execute(
                    f"UPDATE `{child}` SET `{col}` = %s WHERE `{col}` = %s",
                    (new, bumped),
                )
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
    conn.commit()

    with conn.cursor() as cur:
        cur.execute(f"ALTER TABLE `{table}` AUTO_INCREMENT = %s", (n + 1,))
    conn.commit()


def compaction_order(all_tables: Set[str], incoming: Dict[str, List[Tuple[str, str]]]) -> List[str]:
    """
    Orden: primero tablas con menos 'dependencias entrantes' (pocas FK hacia su id),
    para que al compactar las que muchos referencian, los hijos ya tengan ids estables.
    Aquí usamos: orden ascendente por número de tablas hijas que apuntan a `id`.
    """
    ref_count: Dict[str, int] = {t: 0 for t in all_tables}
    for parent, chs in incoming.items():
        if parent in ref_count:
            ref_count[parent] = len(chs)
    # Tablas sin referencias entrantes a id primero
    return sorted(all_tables, key=lambda t: (ref_count.get(t, 0), t))


def compact_all_ids(conn, dry_run: bool, skip_tables: Set[str]) -> None:
    fk_rows = _fk_incoming(conn)
    incoming = _build_incoming_map(fk_rows)
    id_tables = set(_integer_id_tables(conn))
    id_tables.discard("schema_migrations")

    order = compaction_order(id_tables, incoming)
    skipped = [t for t in order if t in skip_tables]
    todo = [t for t in order if t not in skip_tables]
    print(
        f"[2] Compactar id en {len(todo)} tablas "
        f"(se omiten {len(skipped)} tablas ya vaciadas en [1]: {sorted(skip_tables)[:8]}{'…' if len(skip_tables) > 8 else ''})"
    )
    for t in todo:
        try:
            compact_table_ids(conn, t, dry_run, incoming)
        except Exception as e:
            print(f"  ERROR en `{t}`: {e}")
            raise


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Solo mostrar qué haría")
    ap.add_argument("--execute", action="store_true", help="Ejecutar cambios")
    args = ap.parse_args()
    if not args.dry_run and not args.execute:
        ap.error("Indique --dry-run o --execute")

    dry_run = args.dry_run
    conn = _connect()
    try:
        student_tables = _tables_with_column(conn, "student_id")
        truncate_list = list(dict.fromkeys(student_tables + ["students", "folders"]))
        skip_after_truncate = set(truncate_list)

        truncate_students_and_folders(conn, dry_run, truncate_list=truncate_list)
        compact_all_ids(conn, dry_run, skip_tables=skip_after_truncate)
        if not dry_run:
            print("Listo.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
