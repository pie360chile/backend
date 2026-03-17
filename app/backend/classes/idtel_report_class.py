"""Document 9 – Informe fonoaudiológico IDTEL."""
import json
from datetime import datetime
from typing import Any, Optional
from sqlalchemy.orm import Session
from app.backend.db.models import IdtelReportModel


class IdtelReportClass:
    def __init__(self, db: Session):
        self.db = db

    def _to_dict(self, r: IdtelReportModel) -> dict:
        data = {"id": r.id, "student_id": r.student_id, "document_type_id": r.document_type_id, "quantitative_locked": r.quantitative_locked}
        if r.form_data:
            try:
                data.update(json.loads(r.form_data))
            except Exception:
                pass
        if r.added_date:
            data["added_date"] = r.added_date.isoformat()
        if r.updated_date:
            data["updated_date"] = r.updated_date.isoformat()
        return data

    def get(self, id: int) -> Any:
        try:
            r = self.db.query(IdtelReportModel).filter(IdtelReportModel.id == id).first()
            if r:
                return self._to_dict(r)
            return {"status": "error", "message": "Informe IDTEL no encontrado."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_by_student_id(self, student_id: int) -> Any:
        try:
            r = (
                self.db.query(IdtelReportModel)
                .filter(IdtelReportModel.student_id == student_id)
                .order_by(IdtelReportModel.id.desc())
                .first()
            )
            if r:
                return self._to_dict(r)
            return {"status": "error", "message": "No hay informe IDTEL para el estudiante."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def store(self, payload: dict) -> Any:
        try:
            student_id = payload.get("student_id")
            document_type_id = payload.get("document_type_id", 9)
            quantitative_locked = payload.get("quantitative_locked", False)
            form_data = {k: v for k, v in payload.items() if k not in ("student_id", "document_type_id", "quantitative_locked")}
            now = datetime.now()
            row = IdtelReportModel(
                student_id=student_id,
                document_type_id=document_type_id,
                form_data=json.dumps(form_data) if form_data else None,
                quantitative_locked=bool(quantitative_locked),
                added_date=now,
                updated_date=now,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Informe IDTEL creado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, payload: dict) -> Any:
        try:
            row = self.db.query(IdtelReportModel).filter(IdtelReportModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Informe IDTEL no encontrado."}
            quantitative_locked = payload.get("quantitative_locked")
            if quantitative_locked is not None:
                row.quantitative_locked = bool(quantitative_locked)
            form_data = {k: v for k, v in payload.items() if k not in ("student_id", "document_type_id", "quantitative_locked", "id")}
            if form_data:
                row.form_data = json.dumps(form_data)
            row.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Informe IDTEL actualizado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
