"""Catálogo de informes de evaluación por área (ids 54–59)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.backend.db.models import DocumentModel

# (id, career_type_id, nombre) — sincronizar con admin-frontend/src/constants/evaluationAreas.ts
EVALUATION_AREA_CATALOG: tuple[tuple[int, int, str], ...] = (
    (54, 5, "Informe de evaluación por área — Fonoaudiológica"),
    (55, 4, "Informe de evaluación por área — Kinesiológica"),
    (56, 2, "Informe de evaluación por área — Psicológica"),
    (57, 6, "Informe de evaluación por área — Psicopedagógica"),
    (58, 3, "Informe de evaluación por área — Terapia ocupacional"),
    (59, 7, "Informe de evaluación por área — Otras pautas"),
)

EVALUATION_AREA_DOCUMENT_IDS: frozenset[int] = frozenset(row[0] for row in EVALUATION_AREA_CATALOG)

_AREA_NAME_HINT = "Informe de evaluación por área"


def ensure_evaluation_area_catalog_document(db: Session, document_id: int) -> Optional[DocumentModel]:
    """Crea o reactiva la fila de catálogo 54–59. Si el id ya es otro documento, busca/crea por nombre."""
    spec = next((row for row in EVALUATION_AREA_CATALOG if row[0] == int(document_id)), None)
    if spec is None:
        return None

    doc_id, career_id, name = spec
    now = datetime.now()

    row = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if row is not None:
        current = (row.document or "").strip()
        if (not current) or current == name or _AREA_NAME_HINT in current:
            row.document_type_id = 2
            row.career_type_id = career_id
            row.document = name
            row.deleted_date = None
            row.updated_date = now
            db.commit()
            db.refresh(row)
            return row

        by_name = (
            db.query(DocumentModel)
            .filter(DocumentModel.document == name, DocumentModel.deleted_date.is_(None))
            .first()
        )
        if by_name is not None:
            return by_name

        created = DocumentModel(
            document_type_id=2,
            career_type_id=career_id,
            document=name,
            added_date=now,
            updated_date=now,
            deleted_date=None,
        )
        db.add(created)
        db.commit()
        db.refresh(created)
        return created

    row = DocumentModel(
        id=doc_id,
        document_type_id=2,
        career_type_id=career_id,
        document=name,
        added_date=now,
        updated_date=now,
        deleted_date=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
