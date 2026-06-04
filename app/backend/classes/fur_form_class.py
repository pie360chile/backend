"""Document 6 – Formulario de revaluación (FUR)."""
import json
from datetime import datetime
from typing import Any, Optional
from sqlalchemy.orm import Session
from app.backend.db.models import FurFormModel


class FurFormClass:
    RESERVED_KEYS = frozenset(
        {
            "student_id",
            "school_id",
            "student_identification_number",
            "document_type_id",
            "fur_variant",
            "id",
            "added_date",
            "updated_date",
        }
    )

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _resolve_student_rut(payload: dict) -> Optional[str]:
        raw = payload.get("student_identification_number") or payload.get("identification_number")
        if raw is None:
            return None
        text = str(raw).strip()
        return text or None

    @staticmethod
    def _resolve_school_id(payload: dict) -> Optional[int]:
        raw = payload.get("school_id")
        if raw is None or raw == "":
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def _to_dict(self, row: FurFormModel) -> dict:
        data = {
            "id": row.id,
            "student_id": row.student_id,
            "school_id": row.school_id,
            "student_identification_number": row.student_identification_number,
            "document_type_id": row.document_type_id,
            "fur_variant": row.fur_variant or "dea",
        }
        if row.form_data:
            try:
                data.update(json.loads(row.form_data))
            except Exception:
                pass
        # Columnas dedicadas tienen prioridad sobre JSON legacy
        data["school_id"] = row.school_id
        data["student_identification_number"] = row.student_identification_number
        if row.student_identification_number:
            data["identification_number"] = row.student_identification_number
        if row.added_date:
            data["added_date"] = row.added_date.isoformat()
        if row.updated_date:
            data["updated_date"] = row.updated_date.isoformat()
        return data

    def get(self, id: int) -> Any:
        try:
            row = self.db.query(FurFormModel).filter(FurFormModel.id == id).first()
            if row:
                return self._to_dict(row)
            return {"status": "error", "message": "Formulario FUR no encontrado."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_by_student_id(self, student_id: int, fur_variant: Optional[str] = None) -> Any:
        try:
            query = self.db.query(FurFormModel).filter(FurFormModel.student_id == student_id)
            if fur_variant:
                query = query.filter(FurFormModel.fur_variant == fur_variant)
            row = query.order_by(FurFormModel.id.desc()).first()
            if row:
                return self._to_dict(row)
            return {"status": "error", "message": "No hay formulario FUR para el estudiante."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def store(self, payload: dict) -> Any:
        try:
            student_id = payload.get("student_id")
            document_type_id = payload.get("document_type_id", 6)
            fur_variant = (payload.get("fur_variant") or "dea").strip() or "dea"
            school_id = self._resolve_school_id(payload)
            student_rut = self._resolve_student_rut(payload)
            form_data = {k: v for k, v in payload.items() if k not in self.RESERVED_KEYS}
            now = datetime.now()
            row = FurFormModel(
                student_id=student_id,
                school_id=school_id,
                student_identification_number=student_rut,
                document_type_id=document_type_id,
                fur_variant=fur_variant,
                form_data=json.dumps(form_data, ensure_ascii=False) if form_data else None,
                added_date=now,
                updated_date=now,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Formulario FUR guardado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, payload: dict) -> Any:
        try:
            row = self.db.query(FurFormModel).filter(FurFormModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Formulario FUR no encontrado."}
            if payload.get("fur_variant"):
                row.fur_variant = str(payload.get("fur_variant")).strip() or row.fur_variant
            school_id = self._resolve_school_id(payload)
            if school_id is not None:
                row.school_id = school_id
            student_rut = self._resolve_student_rut(payload)
            if student_rut is not None:
                row.student_identification_number = student_rut
            form_data = {k: v for k, v in payload.items() if k not in self.RESERVED_KEYS}
            if form_data:
                row.form_data = json.dumps(form_data, ensure_ascii=False)
            row.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Formulario FUR actualizado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
