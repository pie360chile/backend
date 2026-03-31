"""Document 41 – Informe de evaluación psicomotriz."""
import json
from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session
from app.backend.db.models import Document41PsychomotorReportModel


class Document41ReportClass:
    def __init__(self, db: Session):
        self.db = db

    def _to_dict(self, r: Document41PsychomotorReportModel) -> dict:
        data = {"id": r.id, "student_id": r.student_id, "document_type_id": r.document_type_id}
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
            r = self.db.query(Document41PsychomotorReportModel).filter(Document41PsychomotorReportModel.id == id).first()
            if r:
                return self._to_dict(r)
            return {"status": "error", "message": "Informe no encontrado."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_by_student_id(self, student_id: int) -> Any:
        try:
            r = (
                self.db.query(Document41PsychomotorReportModel)
                .filter(Document41PsychomotorReportModel.student_id == student_id)
                .order_by(Document41PsychomotorReportModel.id.desc())
                .first()
            )
            if r:
                return self._to_dict(r)
            return {"status": "error", "message": "No hay informe para el estudiante."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def store(self, payload: dict) -> Any:
        try:
            student_id = payload.get("student_id")
            document_type_id = payload.get("document_type_id", 41)
            form_data = {k: v for k, v in payload.items() if k not in ("student_id", "document_type_id")}
            now = datetime.now()
            row = Document41PsychomotorReportModel(
                student_id=student_id,
                document_type_id=document_type_id,
                form_data=json.dumps(form_data, ensure_ascii=False) if form_data else None,
                added_date=now,
                updated_date=now,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Informe creado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, payload: dict) -> Any:
        try:
            row = self.db.query(Document41PsychomotorReportModel).filter(Document41PsychomotorReportModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Informe no encontrado."}
            form_data = {k: v for k, v in payload.items() if k not in ("student_id", "document_type_id", "id")}
            if form_data:
                row.form_data = json.dumps(form_data, ensure_ascii=False)
            row.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Informe actualizado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
