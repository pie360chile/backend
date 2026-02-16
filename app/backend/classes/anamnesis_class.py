# Anamnesis (documento tipo 3)
from typing import Optional, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, date
import json

from app.backend.db.models import (
    AnamnesisModel,
    AnamnesisInformantModel,
    AnamnesisInterviewerModel,
    AnamnesisHouseholdMemberModel,
    FolderModel,
)

# document_id para anamnesis en folders
ANAMNESIS_DOCUMENT_ID = 3

# Columnas que se guardan como JSON (Text) en la BD
ANAMNESIS_JSON_FIELDS = {
    "native_language_domain",
    "language_used_domain",
    "specialists",
    "first_year_conditions",
    "response_difficulties",
    "response_success",
    "rewards",
    "supporters",
}


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except Exception:
            return None
    return None


def _to_json_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return None


def _from_json_value(value: Optional[str]) -> Any:
    if value is None or value == "":
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


def _anamnesis_model_to_dict(rec: AnamnesisModel) -> dict:
    """Convierte un AnamnesisModel a diccionario para respuesta API."""
    out = {}
    for col in AnamnesisModel.__table__.columns:
        name = col.name
        val = getattr(rec, name, None)
        if name in ANAMNESIS_JSON_FIELDS:
            out[name] = _from_json_value(val)
        elif isinstance(val, date):
            out[name] = val.strftime("%Y-%m-%d") if val else None
        elif isinstance(val, datetime):
            out[name] = val.strftime("%Y-%m-%d %H:%M:%S") if val else None
        else:
            out[name] = val
    fyc = out.get("first_year_conditions")
    if isinstance(fyc, dict) and "otras" in fyc:
        out["first_year_conditions_other_specify"] = fyc.get("otras") or ""
    return out


class AnamnesisClass:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Any:
        """Obtiene una anamnesis por su ID (incluye informantes, entrevistadores y miembros del hogar)."""
        try:
            rec = self.db.query(AnamnesisModel).filter(AnamnesisModel.id == id).first()
            if not rec:
                return {"status": "error", "message": "Anamnesis no encontrada."}
            result = _anamnesis_model_to_dict(rec)
            # Informantes
            informants = (
                self.db.query(AnamnesisInformantModel)
                .filter(AnamnesisInformantModel.anamnesis_id == id)
                .order_by(AnamnesisInformantModel.sort_order, AnamnesisInformantModel.id)
                .all()
            )
            result["informants"] = [
                {
                    "id": i.id,
                    "sort_order": i.sort_order,
                    "name": i.name,
                    "relationship": i.relationship,
                    "presence": i.presence,
                    "interview_date": i.interview_date.strftime("%Y-%m-%d") if i.interview_date else None,
                }
                for i in informants
            ]
            # Entrevistadores
            interviewers = (
                self.db.query(AnamnesisInterviewerModel)
                .filter(AnamnesisInterviewerModel.anamnesis_id == id)
                .order_by(AnamnesisInterviewerModel.sort_order, AnamnesisInterviewerModel.id)
                .all()
            )
            result["interviewers"] = [
                {
                    "id": i.id,
                    "sort_order": i.sort_order,
                    "professional_id": i.professional_id,
                    "role": i.role,
                    "interview_date": i.interview_date.strftime("%Y-%m-%d") if i.interview_date else None,
                }
                for i in interviewers
            ]
            # Miembros del hogar
            household = (
                self.db.query(AnamnesisHouseholdMemberModel)
                .filter(AnamnesisHouseholdMemberModel.anamnesis_id == id)
                .order_by(AnamnesisHouseholdMemberModel.sort_order, AnamnesisHouseholdMemberModel.id)
                .all()
            )
            result["household_members"] = [
                {
                    "id": h.id,
                    "sort_order": h.sort_order,
                    "name": h.name,
                    "relationship": h.relationship,
                    "age": h.age,
                    "schooling": h.schooling,
                    "occupation": h.occupation,
                }
                for h in household
            ]
            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_by_student_id(self, student_id: int) -> Any:
        """Obtiene la anamnesis más reciente de un estudiante por student_id."""
        try:
            rec = (
                self.db.query(AnamnesisModel)
                .filter(AnamnesisModel.student_id == student_id)
                .order_by(AnamnesisModel.id.desc())
                .first()
            )
            if not rec:
                return {"status": "error", "message": "No se encontró anamnesis para este estudiante."}
            return self.get(rec.id)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_all(
        self,
        student_id: Optional[int] = None,
        page: Optional[int] = None,
        per_page: int = 10,
    ) -> Any:
        """Lista anamnesis; opcionalmente filtrada por student_id y paginada."""
        try:
            query = self.db.query(AnamnesisModel)
            if student_id is not None:
                query = query.filter(AnamnesisModel.student_id == student_id)
            query = query.order_by(AnamnesisModel.id.desc())
            if page is not None and per_page > 0:
                query = query.offset((page - 1) * per_page).limit(per_page)
            rows = query.all()
            return [_anamnesis_model_to_dict(r) for r in rows]
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _apply_data_to_model(self, rec: AnamnesisModel, data: dict) -> None:
        """Aplica los campos de data al modelo (sin informants/interviewers/household_members)."""
        skip = {"id", "informants", "interviewers", "household_members", "born_date", "birth_type_id", "birth_type", "first_year_conditions_other_specify"}
        born_date = data.get("born_date")
        if born_date is not None:
            rec.born_date = _parse_date(born_date)
        # birth_type_id: store y update (acepta birth_type como alias)
        bt_id = data.get("birth_type_id")
        if bt_id is None and "birth_type" in data:
            bt_id = data.get("birth_type")
        if bt_id is not None:
            rec.birth_type_id = int(bt_id) if bt_id != "" else None
        # birth_reason: solo lectura cuando birth_type es normal (1)
        if rec.birth_type_id == 1:
            rec.birth_reason = None
        for key, value in data.items():
            if key in skip:
                continue
            if not hasattr(rec, key):
                continue
            if key in ANAMNESIS_JSON_FIELDS:
                setattr(rec, key, _to_json_value(value))
            else:
                setattr(rec, key, value)

    def store(self, data: dict) -> Any:
        """Crea o actualiza anamnesis: si ya existe para el estudiante, actualiza (borra y recarga informantes, entrevistadores, miembros del hogar); si no, crea nueva."""
        try:
            student_id = data.get("student_id")
            if student_id is None:
                return {"status": "error", "message": "student_id es requerido."}

            # Si ya existe anamnesis para el estudiante, hacer UPDATE
            existing = (
                self.db.query(AnamnesisModel)
                .filter(AnamnesisModel.student_id == student_id)
                .order_by(AnamnesisModel.id.desc())
                .first()
            )
            if existing:
                return self.update(existing.id, data)

            # Crear nueva anamnesis
            last = (
                self.db.query(AnamnesisModel)
                .filter(AnamnesisModel.student_id == student_id)
                .order_by(AnamnesisModel.version.desc())
                .first()
            )
            version = (last.version + 1) if last else 1
            payload = {k: v for k, v in data.items() if k not in ("informants", "interviewers", "household_members")}
            if "first_year_conditions_other_specify" in data:
                fyc = payload.get("first_year_conditions") or {}
                if isinstance(fyc, dict):
                    fyc = dict(fyc)
                    fyc["otras"] = data.get("first_year_conditions_other_specify") or ""
                    payload["first_year_conditions"] = fyc
            payload["version"] = data.get("version") or version
            payload["added_date"] = datetime.now()
            payload["updated_date"] = datetime.now()

            rec = AnamnesisModel(student_id=student_id, version=payload["version"], added_date=payload["added_date"], updated_date=payload["updated_date"])
            self._apply_data_to_model(rec, payload)
            self.db.add(rec)
            self.db.flush()

            # Informantes
            for i, item in enumerate(data.get("informants") or []):
                inv = AnamnesisInformantModel(
                    anamnesis_id=rec.id,
                    sort_order=item.get("sort_order", i),
                    name=item.get("name"),
                    relationship=item.get("relationship"),
                    presence=item.get("presence"),
                    interview_date=_parse_date(item.get("interview_date")),
                )
                self.db.add(inv)
            # Entrevistadores
            for i, item in enumerate(data.get("interviewers") or []):
                inv = AnamnesisInterviewerModel(
                    anamnesis_id=rec.id,
                    sort_order=item.get("sort_order", i),
                    professional_id=item.get("professional_id"),
                    role=item.get("role"),
                    interview_date=_parse_date(item.get("interview_date")),
                )
                self.db.add(inv)
            # Miembros del hogar
            for i, item in enumerate(data.get("household_members") or []):
                h = AnamnesisHouseholdMemberModel(
                    anamnesis_id=rec.id,
                    sort_order=item.get("sort_order", i),
                    name=item.get("name"),
                    relationship=item.get("relationship"),
                    age=item.get("age"),
                    schooling=item.get("schooling"),
                    occupation=item.get("occupation"),
                )
                self.db.add(h)

            # Folder (documento tipo 3)
            last_folder = (
                self.db.query(FolderModel)
                .filter(
                    FolderModel.student_id == student_id,
                    FolderModel.document_id == ANAMNESIS_DOCUMENT_ID,
                )
                .order_by(FolderModel.version_id.desc())
                .first()
            )
            new_version_id = (last_folder.version_id + 1) if last_folder else 1
            folder = FolderModel(
                student_id=student_id,
                document_id=ANAMNESIS_DOCUMENT_ID,
                version_id=new_version_id,
                detail_id=rec.id,
                file=None,
                added_date=datetime.now(),
                updated_date=datetime.now(),
            )
            self.db.add(folder)
            self.db.commit()
            self.db.refresh(rec)
            return {"status": "success", "message": "Anamnesis creada correctamente.", "id": rec.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza una anamnesis existente y reemplaza informantes, entrevistadores y miembros del hogar."""
        try:
            rec = self.db.query(AnamnesisModel).filter(AnamnesisModel.id == id).first()
            if not rec:
                return {"status": "error", "message": "Anamnesis no encontrada."}
            rec.updated_date = datetime.now()
            payload = {k: v for k, v in data.items() if k not in ("informants", "interviewers", "household_members")}
            if "first_year_conditions_other_specify" in data:
                fyc = payload.get("first_year_conditions") or {}
                if isinstance(fyc, dict):
                    fyc = dict(fyc)
                    fyc["otras"] = data.get("first_year_conditions_other_specify") or ""
                    payload["first_year_conditions"] = fyc
            self._apply_data_to_model(rec, payload)

            # Borrar y recrear hijos
            self.db.query(AnamnesisInformantModel).filter(AnamnesisInformantModel.anamnesis_id == id).delete()
            self.db.query(AnamnesisInterviewerModel).filter(AnamnesisInterviewerModel.anamnesis_id == id).delete()
            self.db.query(AnamnesisHouseholdMemberModel).filter(AnamnesisHouseholdMemberModel.anamnesis_id == id).delete()

            for i, item in enumerate(data.get("informants") or []):
                inv = AnamnesisInformantModel(
                    anamnesis_id=id,
                    sort_order=item.get("sort_order", i),
                    name=item.get("name"),
                    relationship=item.get("relationship"),
                    presence=item.get("presence"),
                    interview_date=_parse_date(item.get("interview_date")),
                )
                self.db.add(inv)
            for i, item in enumerate(data.get("interviewers") or []):
                inv = AnamnesisInterviewerModel(
                    anamnesis_id=id,
                    sort_order=item.get("sort_order", i),
                    professional_id=item.get("professional_id"),
                    role=item.get("role"),
                    interview_date=_parse_date(item.get("interview_date")),
                )
                self.db.add(inv)
            for i, item in enumerate(data.get("household_members") or []):
                h = AnamnesisHouseholdMemberModel(
                    anamnesis_id=id,
                    sort_order=item.get("sort_order", i),
                    name=item.get("name"),
                    relationship=item.get("relationship"),
                    age=item.get("age"),
                    schooling=item.get("schooling"),
                    occupation=item.get("occupation"),
                )
                self.db.add(h)

            self.db.commit()
            self.db.refresh(rec)
            return {"status": "success", "message": "Anamnesis actualizada correctamente.", "id": rec.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
