"""CRUD para tabla document_alerts."""

from datetime import datetime
from typing import Optional, Any

from sqlalchemy.orm import Session
from app.backend.db.models import DocumentAlertModel


def _parse_datetime(v) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str) and v.strip():
        s = v.strip()
        try:
            if len(s) >= 19:
                return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            pass
        try:
            if len(s) >= 19:
                return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d")
        except ValueError:
            pass
    return None


class DocumentAlertClass:
    def __init__(self, db: Session):
        self.db = db

    def get(
        self,
        student_id: Optional[int] = None,
        professional_id: Optional[int] = None,
        document_id: Optional[int] = None,
        include_deleted: bool = False,
    ) -> dict:
        """Lista registros filtrados. Por defecto excluye eliminados (deleted_date IS NOT NULL)."""
        try:
            q = self.db.query(DocumentAlertModel)
            if student_id is not None:
                q = q.filter(DocumentAlertModel.student_id == student_id)
            if professional_id is not None:
                q = q.filter(DocumentAlertModel.professional_id == professional_id)
            if document_id is not None:
                q = q.filter(DocumentAlertModel.document_id == document_id)
            if not include_deleted:
                q = q.filter(DocumentAlertModel.deleted_date.is_(None))
            q = q.order_by(DocumentAlertModel.id.desc())
            rows = q.all()
            data = [
                {
                    "id": r.id,
                    "student_id": r.student_id,
                    "professional_id": r.professional_id,
                    "document_id": r.document_id,
                    "must_be_finish_date": r.must_be_finish_date.isoformat() if r.must_be_finish_date else None,
                    "document_uploaded_date": r.document_uploaded_date.isoformat() if r.document_uploaded_date else None,
                    "added_date": r.added_date.isoformat() if r.added_date else None,
                    "updated_date": r.updated_date.isoformat() if r.updated_date else None,
                    "deleted_date": r.deleted_date.isoformat() if r.deleted_date else None,
                }
                for r in rows
            ]
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> dict:
        """Obtiene un registro por id."""
        try:
            row = self.db.query(DocumentAlertModel).filter(DocumentAlertModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            data = {
                "id": row.id,
                "student_id": row.student_id,
                "professional_id": row.professional_id,
                "document_id": row.document_id,
                "must_be_finish_date": row.must_be_finish_date.isoformat() if row.must_be_finish_date else None,
                "document_uploaded_date": row.document_uploaded_date.isoformat() if row.document_uploaded_date else None,
                "added_date": row.added_date.isoformat() if row.added_date else None,
                "updated_date": row.updated_date.isoformat() if row.updated_date else None,
                "deleted_date": row.deleted_date.isoformat() if row.deleted_date else None,
            }
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> dict:
        """Crea un registro en document_alerts."""
        try:
            must_be = _parse_datetime(data.get("must_be_finish_date"))
            uploaded = _parse_datetime(data.get("document_uploaded_date"))
            row = DocumentAlertModel(
                student_id=data["student_id"],
                professional_id=data["professional_id"],
                document_id=data["document_id"],
                must_be_finish_date=must_be,
                document_uploaded_date=uploaded,
                added_date=datetime.utcnow(),
                updated_date=datetime.utcnow(),
                deleted_date=None,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro creado.", "id": row.id, "data": {"id": row.id}}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}

    def update(self, id: int, data: dict) -> dict:
        """Actualiza un registro por id."""
        try:
            row = self.db.query(DocumentAlertModel).filter(DocumentAlertModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if data.get("student_id") is not None:
                row.student_id = data["student_id"]
            if data.get("professional_id") is not None:
                row.professional_id = data["professional_id"]
            if data.get("document_id") is not None:
                row.document_id = data["document_id"]
            if "must_be_finish_date" in data:
                row.must_be_finish_date = _parse_datetime(data["must_be_finish_date"])
            if "document_uploaded_date" in data:
                row.document_uploaded_date = _parse_datetime(data["document_uploaded_date"])
            row.updated_date = datetime.utcnow()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro actualizado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int, soft: bool = True) -> dict:
        """Elimina por id. soft=True hace soft delete (deleted_date = now)."""
        try:
            row = self.db.query(DocumentAlertModel).filter(DocumentAlertModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if soft:
                row.deleted_date = datetime.utcnow()
                row.updated_date = datetime.utcnow()
                self.db.commit()
                return {"status": "success", "message": "Registro eliminado (soft)."}
            self.db.delete(row)
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
