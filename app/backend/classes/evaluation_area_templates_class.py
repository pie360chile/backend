"""Plantillas personalizadas por área de evaluación (compartidas, no carpeta del alumno)."""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.db.models.evaluation_area_templates import EvaluationAreaTemplateModel

VALID_AREA_IDS = frozenset(
    {
        "fonoaudiologica",
        "kinesiologica",
        "psicologica",
        "psicopedagogica",
        "terapia_ocupacional",
        "otras_pautas",
    }
)


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._\u00c0-\u024f\s-]", "_", (name or "plantilla").strip())
    cleaned = re.sub(r"\s+", "_", cleaned).strip("._")
    return (cleaned or "plantilla")[:180]


def _templates_root() -> Path:
    root = (Path(settings.files_dir).resolve() / "evaluation_area_templates")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _serialize(row: EvaluationAreaTemplateModel) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "customer_id": int(row.customer_id),
        "area_id": row.area_id,
        "name": row.name,
        "original_filename": row.original_filename,
        "has_file": bool(row.stored_path),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class EvaluationAreaTemplatesClass:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _customer_id(self, customer_id: int | None) -> int:
        return int(customer_id or 0)

    def _get(self, template_id: int, customer_id: int) -> EvaluationAreaTemplateModel | None:
        return (
            self.db.query(EvaluationAreaTemplateModel)
            .filter(
                EvaluationAreaTemplateModel.id == int(template_id),
                EvaluationAreaTemplateModel.customer_id == int(customer_id),
            )
            .first()
        )

    def list_items(self, customer_id: int | None, area_id: str | None = None) -> list[dict[str, Any]]:
        cid = self._customer_id(customer_id)
        q = self.db.query(EvaluationAreaTemplateModel).filter(
            EvaluationAreaTemplateModel.customer_id == cid
        )
        if area_id:
            if area_id not in VALID_AREA_IDS:
                return []
            q = q.filter(EvaluationAreaTemplateModel.area_id == area_id)
        rows = q.order_by(EvaluationAreaTemplateModel.name.asc()).all()
        return [_serialize(r) for r in rows]

    def create(
        self,
        *,
        customer_id: int | None,
        area_id: str,
        name: str,
        filename: str,
        data: bytes,
        content_type: str | None,
        user_id: int | None,
    ) -> dict[str, Any]:
        if area_id not in VALID_AREA_IDS:
            return {"status": "error", "message": "Área no válida.", "http_status": 400}
        label = (name or "").strip()
        if not label:
            return {"status": "error", "message": "Indique el nombre de la plantilla.", "http_status": 400}
        if len(label) > 255:
            return {"status": "error", "message": "El nombre es demasiado largo.", "http_status": 400}
        if not data:
            return {"status": "error", "message": "Archivo vacío.", "http_status": 400}
        lower = (filename or "").lower()
        if not lower.endswith((".pdf", ".doc", ".docx")):
            return {
                "status": "error",
                "message": "Solo se permiten archivos .pdf, .doc o .docx.",
                "http_status": 400,
            }

        cid = self._customer_id(customer_id)
        exists = (
            self.db.query(EvaluationAreaTemplateModel)
            .filter(
                EvaluationAreaTemplateModel.customer_id == cid,
                EvaluationAreaTemplateModel.area_id == area_id,
                EvaluationAreaTemplateModel.name == label,
            )
            .first()
        )
        if exists:
            return {
                "status": "error",
                "message": "Ya existe una plantilla con ese nombre en esta área.",
                "http_status": 409,
            }

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        row = EvaluationAreaTemplateModel(
            customer_id=cid,
            area_id=area_id,
            name=label,
            original_filename=filename or "plantilla.docx",
            stored_path="",
            content_type=content_type,
            uploaded_by=user_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.flush()

        folder = _templates_root() / f"c{cid}" / f"t{int(row.id)}"
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True, exist_ok=True)
        safe_name = _safe_filename(filename)
        target = folder / safe_name
        target.write_bytes(data)
        row.stored_path = str(target.relative_to(Path(settings.files_dir).resolve())).replace("\\", "/")
        self.db.commit()
        self.db.refresh(row)
        return {
            "status": "success",
            "message": "Plantilla guardada.",
            "data": _serialize(row),
        }

    def replace_file(
        self,
        template_id: int,
        customer_id: int | None,
        filename: str,
        data: bytes,
        content_type: str | None,
        user_id: int | None,
    ) -> dict[str, Any]:
        cid = self._customer_id(customer_id)
        row = self._get(template_id, cid)
        if not row:
            return {"status": "error", "message": "Plantilla no encontrada.", "http_status": 404}
        if not data:
            return {"status": "error", "message": "Archivo vacío.", "http_status": 400}
        lower = (filename or "").lower()
        if not lower.endswith((".pdf", ".doc", ".docx")):
            return {
                "status": "error",
                "message": "Solo se permiten archivos .pdf, .doc o .docx.",
                "http_status": 400,
            }

        folder = _templates_root() / f"c{cid}" / f"t{int(row.id)}"
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True, exist_ok=True)
        safe_name = _safe_filename(filename)
        target = folder / safe_name
        target.write_bytes(data)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        row.original_filename = filename or safe_name
        row.stored_path = str(target.relative_to(Path(settings.files_dir).resolve())).replace("\\", "/")
        row.content_type = content_type
        row.uploaded_by = user_id
        row.updated_at = now
        self.db.commit()
        self.db.refresh(row)
        return {"status": "success", "message": "Plantilla actualizada.", "data": _serialize(row)}

    def get_row(self, template_id: int, customer_id: int | None) -> EvaluationAreaTemplateModel | None:
        return self._get(template_id, self._customer_id(customer_id))

    def absolute_path(self, row: EvaluationAreaTemplateModel) -> Path | None:
        if not row.stored_path:
            return None
        path = (Path(settings.files_dir).resolve() / row.stored_path).resolve()
        root = Path(settings.files_dir).resolve()
        if not str(path).startswith(str(root)) or not path.is_file():
            return None
        return path
