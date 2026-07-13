"""CRUD for downloadable format models of simple-upload documents."""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.db.models.document_format_models import DocumentFormatModel
from app.backend.db.models.pie_core import DocumentModel
from app.backend.utils.simple_upload_documents import (
    SIMPLE_UPLOAD_DOC_ORDER,
    SIMPLE_UPLOAD_DOCUMENT_IDS,
)


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._\u00c0-\u024f\s-]", "_", (name or "modelo").strip())
    cleaned = re.sub(r"\s+", "_", cleaned).strip("._")
    return (cleaned or "modelo")[:180]


def _models_root() -> Path:
    root = (Path(settings.files_dir).resolve() / "document_format_models")
    root.mkdir(parents=True, exist_ok=True)
    return root


class DocumentFormatModelsClass:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_items(self) -> list[dict[str, Any]]:
        docs = (
            self.db.query(DocumentModel)
            .filter(
                DocumentModel.id.in_(list(SIMPLE_UPLOAD_DOCUMENT_IDS)),
                DocumentModel.deleted_date.is_(None),
            )
            .all()
        )
        by_id = {int(d.id): d for d in docs}
        models = {
            int(m.document_id): m
            for m in self.db.query(DocumentFormatModel).filter(
                DocumentFormatModel.document_id.in_(list(SIMPLE_UPLOAD_DOCUMENT_IDS))
            )
        }
        order_index = {name: i for i, name in enumerate(SIMPLE_UPLOAD_DOC_ORDER)}
        items: list[dict[str, Any]] = []
        for doc_id in SIMPLE_UPLOAD_DOCUMENT_IDS:
            doc = by_id.get(doc_id)
            if not doc:
                continue
            model = models.get(doc_id)
            items.append(
                {
                    "document_id": doc_id,
                    "document_name": doc.document or f"Documento {doc_id}",
                    "career_type_id": doc.career_type_id,
                    "section_id": doc.document_type_id,
                    "has_model": model is not None,
                    "model_id": model.id if model else None,
                    "original_filename": model.original_filename if model else None,
                    "updated_at": model.updated_at.isoformat() if model and model.updated_at else None,
                }
            )
        items.sort(
            key=lambda row: (
                order_index.get(row["document_name"], 10_000),
                row["document_name"].lower(),
            )
        )
        return items

    def get_model(self, document_id: int) -> DocumentFormatModel | None:
        return (
            self.db.query(DocumentFormatModel)
            .filter(DocumentFormatModel.document_id == int(document_id))
            .first()
        )

    def upload(
        self,
        document_id: int,
        filename: str,
        data: bytes,
        content_type: str | None,
        user_id: int | None,
    ) -> dict[str, Any]:
        if int(document_id) not in SIMPLE_UPLOAD_DOCUMENT_IDS:
            return {
                "status": "error",
                "message": "Este documento no admite modelo de solo carga.",
                "http_status": 400,
            }
        doc = (
            self.db.query(DocumentModel)
            .filter(DocumentModel.id == int(document_id), DocumentModel.deleted_date.is_(None))
            .first()
        )
        if not doc:
            return {"status": "error", "message": "Documento no encontrado.", "http_status": 404}
        if not data:
            return {"status": "error", "message": "Archivo vacío.", "http_status": 400}

        lower = (filename or "").lower()
        if not lower.endswith((".pdf", ".doc", ".docx")):
            return {
                "status": "error",
                "message": "Solo se permiten archivos .pdf, .doc o .docx.",
                "http_status": 400,
            }

        folder = _models_root() / f"d{int(document_id)}"
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True, exist_ok=True)
        safe_name = _safe_filename(filename)
        target = folder / safe_name
        target.write_bytes(data)
        rel = str(target.relative_to(Path(settings.files_dir).resolve())).replace("\\", "/")

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        row = self.get_model(document_id)
        if row:
            row.original_filename = filename or safe_name
            row.stored_path = rel
            row.content_type = content_type
            row.uploaded_by = user_id
            row.updated_at = now
        else:
            row = DocumentFormatModel(
                document_id=int(document_id),
                original_filename=filename or safe_name,
                stored_path=rel,
                content_type=content_type,
                uploaded_by=user_id,
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return {
            "status": "success",
            "message": "Modelo guardado.",
            "data": {
                "document_id": int(document_id),
                "model_id": row.id,
                "original_filename": row.original_filename,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            },
        }

    def absolute_path(self, row: DocumentFormatModel) -> Path | None:
        if not row.stored_path:
            return None
        path = (Path(settings.files_dir).resolve() / row.stored_path).resolve()
        root = Path(settings.files_dir).resolve()
        if not str(path).startswith(str(root)) or not path.is_file():
            return None
        return path

    def delete(self, document_id: int) -> dict[str, Any]:
        row = self.get_model(document_id)
        if not row:
            return {"status": "error", "message": "No hay modelo cargado.", "http_status": 404}
        folder = _models_root() / f"d{int(document_id)}"
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
        self.db.delete(row)
        self.db.commit()
        return {"status": "success", "message": "Modelo eliminado."}
