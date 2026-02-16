from typing import Optional, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, date, time
from app.backend.db.models import GuardianAttendanceCertificateModel


def _parse_date(value) -> Optional[date]:
    """Convierte string a date si es necesario."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    return None


def _parse_time(value) -> Optional[time]:
    """Convierte string a time si es necesario (HH:MM o HH:MM:SS)."""
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(s, fmt).time()
            except ValueError:
                continue
    return None


class GuardianAttendanceCertificateClass:
    def __init__(self, db: Session):
        self.db = db

    def _to_dict(self, obj: GuardianAttendanceCertificateModel) -> dict:
        """Convierte el modelo a dict para respuesta."""
        def _time_str(t):
            if t is None:
                return None
            return t.strftime("%H:%M") if hasattr(t, "strftime") else str(t)
        return {
            "id": obj.id,
            "student_id": obj.student_id,
            "document_type_id": obj.document_type_id,
            "professional_id": obj.professional_id,
            "certificate_date": obj.certificate_date.strftime("%Y-%m-%d") if obj.certificate_date else None,
            "start_time": _time_str(obj.start_time),
            "end_time": _time_str(obj.end_time),
            "added_date": obj.added_date.strftime("%Y-%m-%d %H:%M:%S") if obj.added_date else None,
            "updated_date": obj.updated_date.strftime("%Y-%m-%d %H:%M:%S") if obj.updated_date else None,
        }

    def get(self, id: int) -> Any:
        """Obtiene un certificado por ID."""
        try:
            obj = self.db.query(GuardianAttendanceCertificateModel).filter(GuardianAttendanceCertificateModel.id == id).first()
            if obj:
                return self._to_dict(obj)
            return {"status": "error", "message": "Certificado no encontrado."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_by_student_id(self, student_id: int) -> Any:
        """Obtiene el certificado más reciente por student_id."""
        try:
            obj = (
                self.db.query(GuardianAttendanceCertificateModel)
                .filter(
                    GuardianAttendanceCertificateModel.student_id == student_id,
                    GuardianAttendanceCertificateModel.document_type_id == 25,
                )
                .order_by(GuardianAttendanceCertificateModel.id.desc())
                .first()
            )
            if obj:
                return self._to_dict(obj)
            return {"status": "error", "message": "No se encontró certificado de asistencia del apoderado para este estudiante."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_all(self, student_id: Optional[int] = None) -> Any:
        """Lista certificados, opcionalmente filtrados por student_id."""
        try:
            query = self.db.query(GuardianAttendanceCertificateModel).filter(
                GuardianAttendanceCertificateModel.document_type_id == 25
            )
            if student_id is not None:
                query = query.filter(GuardianAttendanceCertificateModel.student_id == student_id)
            items = query.order_by(GuardianAttendanceCertificateModel.id.desc()).all()
            return [self._to_dict(i) for i in items]
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def store(self, data: dict) -> Any:
        """Crea un nuevo certificado. Si ya existe uno para el estudiante, puede actualizarse o crearse otro según criterio."""
        try:
            student_id = data.get("student_id")
            if student_id is None:
                return {"status": "error", "message": "student_id es requerido."}

            new_obj = GuardianAttendanceCertificateModel(
                student_id=student_id,
                document_type_id=data.get("document_type_id", 25),
                professional_id=data.get("professional_id"),
                certificate_date=_parse_date(data.get("certificate_date")),
                start_time=_parse_time(data.get("start_time")),
                end_time=_parse_time(data.get("end_time")),
            )
            self.db.add(new_obj)
            self.db.commit()
            self.db.refresh(new_obj)
            return {"status": "success", "message": "Certificado creado exitosamente", "id": new_obj.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza un certificado existente."""
        try:
            obj = self.db.query(GuardianAttendanceCertificateModel).filter(GuardianAttendanceCertificateModel.id == id).first()
            if not obj:
                return {"status": "error", "message": "Certificado no encontrado."}

            date_fields = {"certificate_date"}
            time_fields = {"start_time", "end_time"}

            for key, value in data.items():
                if hasattr(obj, key):
                    if key in date_fields:
                        setattr(obj, key, _parse_date(value))
                    elif key in time_fields:
                        setattr(obj, key, _parse_time(value))
                    else:
                        setattr(obj, key, value)

            obj.updated_date = datetime.utcnow()
            self.db.commit()
            self.db.refresh(obj)
            return {"status": "success", "message": "Certificado actualizado exitosamente", "id": obj.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        """Elimina un certificado."""
        try:
            obj = self.db.query(GuardianAttendanceCertificateModel).filter(GuardianAttendanceCertificateModel.id == id).first()
            if not obj:
                return {"status": "error", "message": "Certificado no encontrado."}
            self.db.delete(obj)
            self.db.commit()
            return {"status": "success", "message": "Certificado eliminado exitosamente"}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
