from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.backend.db.models import MeetingSchedualingAgreementModel


def _row_to_dict(r: MeetingSchedualingAgreementModel) -> dict:
    return {
        "id": r.id,
        "meeting_schedualing_id": r.meeting_schedualing_id,
        "agreements": r.agreements,
        "added_date": r.added_date.isoformat() if r.added_date else None,
        "updated_date": r.updated_date.isoformat() if r.updated_date else None,
        "deleted_date": r.deleted_date.isoformat() if r.deleted_date else None,
    }


class MeetingSchedualingAgreementClass:
    def __init__(self, db: Session):
        self.db = db

    def get(
        self,
        meeting_schedualing_id: Optional[int] = None,
    ) -> Any:
        """Lista registros activos (deleted_date is None). Filtro opcional por meeting_schedualing_id (-1 o None = no filtrar)."""
        try:
            q = (
                self.db.query(MeetingSchedualingAgreementModel)
                .filter(MeetingSchedualingAgreementModel.deleted_date.is_(None))
            )
            if meeting_schedualing_id is not None and meeting_schedualing_id != -1:
                q = q.filter(MeetingSchedualingAgreementModel.meeting_schedualing_id == meeting_schedualing_id)
            rows = q.all()
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene un registro por id."""
        try:
            row = self.db.query(MeetingSchedualingAgreementModel).filter(MeetingSchedualingAgreementModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        """Crea o actualiza: si ya existe un registro (activo o borrado) con el mismo meeting_schedualing_id, actualiza; si no, crea uno nuevo."""
        try:
            now = datetime.now()
            mid = data.get("meeting_schedualing_id")
            row = (
                self.db.query(MeetingSchedualingAgreementModel)
                .filter(MeetingSchedualingAgreementModel.meeting_schedualing_id == mid)
                .first()
            )
            if row:
                row.agreements = data.get("agreements")
                row.updated_date = now
                row.deleted_date = None
                self.db.commit()
                self.db.refresh(row)
                return {"status": "success", "message": "Registro actualizado.", "id": row.id, "data": _row_to_dict(row)}
            row = MeetingSchedualingAgreementModel(
                meeting_schedualing_id=mid,
                agreements=data.get("agreements"),
                added_date=now,
                updated_date=now,
                deleted_date=None,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro creado.", "id": row.id, "data": _row_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza un registro; solo los campos enviados."""
        try:
            row = self.db.query(MeetingSchedualingAgreementModel).filter(MeetingSchedualingAgreementModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "meeting_schedualing_id" in data and data["meeting_schedualing_id"] is not None:
                row.meeting_schedualing_id = data["meeting_schedualing_id"]
            if "agreements" in data:
                row.agreements = data["agreements"]
            row.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro actualizado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        """Borrado lógico: setea deleted_date."""
        try:
            row = self.db.query(MeetingSchedualingAgreementModel).filter(MeetingSchedualingAgreementModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = datetime.now()
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
