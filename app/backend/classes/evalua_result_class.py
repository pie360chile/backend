"""Informes Resultado Prueba Evalua (título persistido en evalua_result_report)."""
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.backend.db.models import EvaluaResultReportModel


class EvaluaResultClass:
    def __init__(self, db: Session):
        self.db = db

    def _row_to_data(self, r: EvaluaResultReportModel) -> dict:
        return {
            "id": r.id,
            "detail_id": r.id,
            "student_id": r.student_id,
            "document_catalog_id": r.document_catalog_id,
            "title": (r.title or "").strip(),
            "added_date": r.added_date.isoformat() if r.added_date else None,
            "updated_date": r.updated_date.isoformat() if r.updated_date else None,
        }

    def get_by_student(self, student_id: int, document_catalog_id: int = 42) -> Any:
        """Solo lectura: no crea ni modifica filas."""
        try:
            r = (
                self.db.query(EvaluaResultReportModel)
                .filter(
                    EvaluaResultReportModel.student_id == student_id,
                    EvaluaResultReportModel.document_catalog_id == document_catalog_id,
                )
                .order_by(EvaluaResultReportModel.id.desc())
                .first()
            )
            if not r:
                return {"status": "success", "data": None}
            return {"status": "success", "data": self._row_to_data(r)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def upsert_title(self, student_id: int, document_catalog_id: int, title: str) -> Any:
        """
        Cada subida crea una fila nueva (historial por versión de archivo en catálogo 42).
        Sin commit propio: misma transacción que `folders` en el POST upload.
        """
        try:
            t = (title or "").strip()
            if not t:
                return {"status": "error", "message": "El título es obligatorio."}
            now = datetime.now()
            row = EvaluaResultReportModel(
                student_id=student_id,
                document_catalog_id=document_catalog_id,
                title=t,
                added_date=now,
                updated_date=now,
            )
            self.db.add(row)
            self.db.flush()
            self.db.refresh(row)
            return {"status": "success", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
