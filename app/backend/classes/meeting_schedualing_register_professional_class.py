from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.backend.db.models import MeetingSchedualingRegisterProfessionalModel


def _row_to_dict(r: MeetingSchedualingRegisterProfessionalModel) -> dict:
    return {
        "id": r.id,
        "meeting_schedualing_register_id": r.meeting_schedualing_register_id,
        "professional_id": r.professional_id,
        "added_date": r.added_date.isoformat() if r.added_date else None,
        "updated_date": r.updated_date.isoformat() if r.updated_date else None,
        "deleted_date": r.deleted_date.isoformat() if r.deleted_date else None,
    }


class MeetingSchedualingRegisterProfessionalClass:
    def __init__(self, db: Session):
        self.db = db

    def get(
        self,
        meeting_schedualing_register_id: Optional[int] = None,
        professional_id: Optional[int] = None,
    ) -> Any:
        """Lista registros activos (deleted_date is None). Filtros opcionales (-1 o None = no filtrar)."""
        try:
            q = (
                self.db.query(MeetingSchedualingRegisterProfessionalModel)
                .filter(MeetingSchedualingRegisterProfessionalModel.deleted_date.is_(None))
            )
            if meeting_schedualing_register_id is not None and meeting_schedualing_register_id != -1:
                q = q.filter(MeetingSchedualingRegisterProfessionalModel.meeting_schedualing_register_id == meeting_schedualing_register_id)
            if professional_id is not None and professional_id != -1:
                q = q.filter(MeetingSchedualingRegisterProfessionalModel.professional_id == professional_id)
            rows = q.all()
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene un registro por id."""
        try:
            row = self.db.query(MeetingSchedualingRegisterProfessionalModel).filter(MeetingSchedualingRegisterProfessionalModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        """Crea o actualiza: si ya existe un registro con el mismo (meeting_schedualing_register_id, professional_id), actualiza (o restaura si estaba borrado); si no, crea uno nuevo."""
        try:
            now = datetime.now()
            reg_id = data.get("meeting_schedualing_register_id")
            prof_id = data.get("professional_id")
            row = (
                self.db.query(MeetingSchedualingRegisterProfessionalModel)
                .filter(
                    MeetingSchedualingRegisterProfessionalModel.meeting_schedualing_register_id == reg_id,
                    MeetingSchedualingRegisterProfessionalModel.professional_id == prof_id,
                )
                .first()
            )
            if row:
                row.updated_date = now
                row.deleted_date = None
                self.db.commit()
                self.db.refresh(row)
                return {"status": "success", "message": "Registro actualizado.", "id": row.id, "data": _row_to_dict(row)}
            row = MeetingSchedualingRegisterProfessionalModel(
                meeting_schedualing_register_id=reg_id,
                professional_id=prof_id,
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
        """Actualiza un registro; solo los campos enviados. Acepta 0 como valor válido para los ids."""
        try:
            row = self.db.query(MeetingSchedualingRegisterProfessionalModel).filter(MeetingSchedualingRegisterProfessionalModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "meeting_schedualing_register_id" in data:
                row.meeting_schedualing_register_id = data["meeting_schedualing_register_id"]
            if "professional_id" in data:
                row.professional_id = data["professional_id"]
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
            row = self.db.query(MeetingSchedualingRegisterProfessionalModel).filter(MeetingSchedualingRegisterProfessionalModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = datetime.now()
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete_by_register_and_professional(
        self, meeting_schedualing_register_id: int, professional_id: int
    ) -> Any:
        """Borrado lógico del registro que tiene este meeting_schedualing_register_id y professional_id (el que quitas de la lista)."""
        try:
            row = (
                self.db.query(MeetingSchedualingRegisterProfessionalModel)
                .filter(
                    MeetingSchedualingRegisterProfessionalModel.meeting_schedualing_register_id == meeting_schedualing_register_id,
                    MeetingSchedualingRegisterProfessionalModel.professional_id == professional_id,
                )
                .first()
            )
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = datetime.now()
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def sync_professionals(
        self, meeting_schedualing_register_id: int, professional_ids: list
    ) -> Any:
        """Sincroniza la lista de profesionales: borra (lógico) los que no están en professional_ids, añade/restaura los que sí."""
        try:
            now = datetime.now()
            current = (
                self.db.query(MeetingSchedualingRegisterProfessionalModel)
                .filter(
                    MeetingSchedualingRegisterProfessionalModel.meeting_schedualing_register_id == meeting_schedualing_register_id,
                    MeetingSchedualingRegisterProfessionalModel.deleted_date.is_(None),
                )
                .all()
            )
            ids_set = set(professional_ids or [])
            for row in current:
                if row.professional_id not in ids_set:
                    row.deleted_date = now
                    row.updated_date = now
            for pid in ids_set:
                existing = (
                    self.db.query(MeetingSchedualingRegisterProfessionalModel)
                    .filter(
                        MeetingSchedualingRegisterProfessionalModel.meeting_schedualing_register_id == meeting_schedualing_register_id,
                        MeetingSchedualingRegisterProfessionalModel.professional_id == pid,
                    )
                    .first()
                )
                if existing:
                    existing.deleted_date = None
                    existing.updated_date = now
                else:
                    new_row = MeetingSchedualingRegisterProfessionalModel(
                        meeting_schedualing_register_id=meeting_schedualing_register_id,
                        professional_id=pid,
                        added_date=now,
                        updated_date=now,
                        deleted_date=None,
                    )
                    self.db.add(new_row)
            self.db.commit()
            return {"status": "success", "message": "Lista actualizada.", "data": None}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
