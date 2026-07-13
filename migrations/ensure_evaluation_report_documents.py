"""Ensure evaluation report documents exist in `documents` catalog.

Idempotent: inserts by exact name if missing; fixes Conners career_type_id.

Run from backend/:
  python migrations/ensure_evaluation_report_documents.py
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from app.backend.db.database import engine

# (document name, document_type_id=section, career_type_id)
# Section 2 = Evaluation. Careers: 2 psico, 3 TO, 4 kinesio, 5 fono.
REQUIRED = [
    # 1. Fonoaudiológico
    ("Informe Fonoaudiológico - Evaluación Informal", 2, 5),
    ("Informe Fonoaudiológico - IDTEL", 2, 5),
    ("Informe Fonoaudiológico - PEFE", 2, 5),
    ("Informe Fonoaudiológico - STSG, TECAL y TEPROSIF", 2, 5),
    # 2. Kinesiológica
    ("Informe kinesiológico - Evaluación informal", 2, 4),
    ("Informe Kinesiológica - Vitor Da Fonseca", 2, 4),
    # 3. Psicológica
    ("Informe de conducta adaptativa – ABAS II", 2, 2),
    ("Informe de conducta adaptativa – ICAP", 2, 2),
    ("Informe Psicológico – WAIS IV", 2, 2),
    ("Informe Psicológico – WISC V", 2, 2),
    ("Test de Conners (para docentes abreviada)", 2, 2),
    # 4. Terapia Ocupacional
    ("Informe Terapia Ocupacional - Evaluación Informal", 2, 3),
    ("Informe Terapia Ocupacional - Perfil Sensorial", 2, 3),
    ("Informe Terapia Ocupacional - SPM-2", 2, 3),
]


def main() -> None:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with engine.begin() as conn:
        for name, section_id, career_id in REQUIRED:
            row = conn.execute(
                text(
                    "SELECT id, career_type_id, document_type_id FROM documents "
                    "WHERE document = :name AND deleted_date IS NULL LIMIT 1"
                ),
                {"name": name},
            ).fetchone()
            if row:
                updates = []
                params = {"id": row[0]}
                if row[1] != career_id:
                    updates.append("career_type_id = :career_id")
                    params["career_id"] = career_id
                if row[2] != section_id:
                    updates.append("document_type_id = :section_id")
                    params["section_id"] = section_id
                if updates:
                    updates.append("updated_date = :now")
                    params["now"] = now
                    conn.execute(
                        text(f"UPDATE documents SET {', '.join(updates)} WHERE id = :id"),
                        params,
                    )
                    print(f"updated: id={row[0]} {name}")
                else:
                    print(f"exists: id={row[0]} {name}")
                continue

            conn.execute(
                text(
                    "INSERT INTO documents "
                    "(document_type_id, career_type_id, document, added_date, updated_date) "
                    "VALUES (:section_id, :career_id, :name, :now, :now)"
                ),
                {
                    "section_id": section_id,
                    "career_id": career_id,
                    "name": name,
                    "now": now,
                },
            )
            new_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
            print(f"inserted: id={new_id} {name}")

        # Conners was wrongly tagged as fono (5); force psychology (2) by name.
        conn.execute(
            text(
                "UPDATE documents SET career_type_id = 2, updated_date = :now "
                "WHERE document LIKE :pat AND deleted_date IS NULL"
            ),
            {"now": now, "pat": "%Conners%"},
        )
        print("ok: Conners career_type_id -> 2 (psicología)")


if __name__ == "__main__":
    main()
