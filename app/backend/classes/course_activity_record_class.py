"""IV. Registro de actividades (familia/comunidad/otras) con asistentes — tres tablas por sección."""

from datetime import datetime, date
from enum import Enum
from typing import Optional, Any, List, Dict, Type, Union
import json
from sqlalchemy.orm import Session
from app.backend.db.models import (
    CourseActivityFamilyModel,
    CourseActivityCommunityModel,
    CourseActivityOtherModel,
)

CourseActivityRowModel = Union[
    CourseActivityFamilyModel,
    CourseActivityCommunityModel,
    CourseActivityOtherModel,
]


def _model_for_section(sec: str) -> Type[CourseActivityRowModel]:
    s = normalize_course_activity_section(sec)
    if s == "community":
        return CourseActivityCommunityModel
    if s == "other":
        return CourseActivityOtherModel
    return CourseActivityFamilyModel


def _date_str(v, fmt="%Y-%m-%d %H:%M:%S"):
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if hasattr(v, "strftime"):
        return v.strftime(fmt)
    return str(v)


def _parse_date(s: Optional[str]) -> Optional[date]:
    if s is None or (isinstance(s, str) and not s.strip()):
        return None
    if isinstance(s, date):
        return s
    try:
        return datetime.strptime(str(s).strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def normalize_course_activity_section(v: Optional[Any]) -> str:
    """
    Mapea la sección del registro IV/V a BD: family | community | other.

    UI / lógica: 1=familia, 2=comunidad, 3=otras/acta (V).
    Acepta enteros, strings \"1\"/\"2\"/\"3\", ENUM de MySQL/SQLAlchemy y nombres en inglés.
    """
    if v is None:
        return "family"
    if isinstance(v, bool):
        return "family"
    if isinstance(v, Enum):
        return normalize_course_activity_section(v.value)
    # SQLAlchemy / tipos ENUM propios: a veces NO son enum.Enum pero sí tienen .value
    if not isinstance(v, (str, bytes, int, float, type(None))) and hasattr(v, "value"):
        try:
            inner = getattr(v, "value", None)
            if inner is not None and inner is not v:
                return normalize_course_activity_section(inner)
        except Exception:
            pass
    if isinstance(v, (bytes, bytearray)):
        return normalize_course_activity_section(v.decode("utf-8", errors="replace"))
    if isinstance(v, float) and v == int(v) and int(v) in (1, 2, 3):
        v = int(v)
    if isinstance(v, int):
        return {1: "family", 2: "community", 3: "other"}.get(v, "family")
    s = str(v).strip().lower().strip("'\"")  # algunos drivers añaden comillas al ENUM
    # SQLAlchemy / repr: "...EnumMember.COMMUNITY" → último segmento
    if "." in s:
        tail = s.rsplit(".", 1)[-1].lower()
        if tail in ("family", "community", "other"):
            return tail
        if tail in ("1", "01"):
            return "family"
        if tail in ("2", "02"):
            return "community"
        if tail in ("3", "03"):
            return "other"
    if s in ("1", "01"):
        return "family"
    if s in ("2", "02"):
        return "community"
    if s in ("3", "03"):
        return "other"
    if s in ("family", "community", "other"):
        return s
    if s in ("familia", "familiar"):
        return "family"
    if s in ("comunidad",):
        return "community"
    if s in ("otros", "otra", "otro", "acta", "reuniones"):
        return "other"
    return "family"


def _participant_type_label(v) -> str:
    """1 = Apoderado, 2 = Profesional del establecimiento (coincide con BD/UI)."""
    if v is None:
        return ""
    try:
        pt = int(v)
    except (TypeError, ValueError):
        return ""
    if pt == 1:
        return "Apoderado"
    if pt == 2:
        return "Profesional del establecimiento"
    return ""


def _parse_attendees(v: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    """Serializa asistentes [{id, name, participant_type?, phone?, …}] a JSON string para BD."""
    if v is None:
        return None
    clean: List[Dict[str, Any]] = []
    for item in v:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            attendee_id = item.get("id", 0)
            try:
                attendee_id = int(attendee_id) if attendee_id is not None else 0
            except (ValueError, TypeError):
                attendee_id = 0
            row: Dict[str, Any] = {"id": attendee_id, "name": name}
            pt = item.get("participant_type")
            if pt is not None:
                try:
                    row["participant_type"] = int(pt)
                except (ValueError, TypeError):
                    pass
            role = str(item.get("role") or item.get("tipo") or "").strip()
            phone = str(item.get("phone") or item.get("telefono") or "").strip()
            email = str(item.get("email") or item.get("mail") or "").strip()
            rut = str(item.get("rut") or item.get("identification_number") or "").strip()
            if role:
                row["role"] = role
            if phone:
                row["phone"] = phone
            if email:
                row["email"] = email
            if rut:
                row["rut"] = rut
            clean.append(row)
    return json.dumps(clean, ensure_ascii=False) if clean else None


def _load_attendees(v) -> List[Dict[str, Any]]:
    if v is None or (isinstance(v, str) and not v.strip()):
        return []
    if isinstance(v, list):
        return v
    try:
        data = json.loads(v) if isinstance(v, str) else []
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        attendee_id = item.get("id", 0)
        try:
            attendee_id = int(attendee_id) if attendee_id is not None else 0
        except (ValueError, TypeError):
            attendee_id = 0
        row: Dict[str, Any] = {"id": attendee_id, "name": name}
        pt = item.get("participant_type")
        if pt is not None:
            try:
                row["participant_type"] = int(pt)
            except (ValueError, TypeError):
                pass
        role = str(item.get("role") or item.get("tipo") or "").strip()
        phone = str(item.get("phone") or item.get("telefono") or "").strip()
        email = str(item.get("email") or item.get("mail") or "").strip()
        rut = str(item.get("rut") or item.get("identification_number") or "").strip()
        if role:
            row["role"] = role
        if phone:
            row["phone"] = phone
        if email:
            row["email"] = email
        if rut:
            row["rut"] = rut
        out.append(row)
    return out


def attendees_rafcnia_line(attendees: List[Dict[str, Any]]) -> str:
    """Texto para columna «apoderado o profesional» (mismo orden que nombres)."""
    parts: List[str] = []
    for a in attendees:
        r = str(a.get("role") or a.get("tipo") or "").strip()
        if not r:
            r = _participant_type_label(a.get("participant_type"))
        parts.append(r if r else "—")
    return "; ".join(parts)


def attendees_rafcnit_line(attendees: List[Dict[str, Any]]) -> str:
    """Texto para columna teléfono/mail (mismo orden que nombres)."""
    parts: List[str] = []
    for a in attendees:
        phone = str(a.get("phone") or a.get("telefono") or "").strip()
        email = str(a.get("email") or a.get("mail") or "").strip()
        if phone and email:
            parts.append(f"{phone} / {email}")
        elif phone:
            parts.append(phone)
        elif email:
            parts.append(email)
        else:
            parts.append("—")
    return "; ".join(parts)


def attendee_rut_cell(a: Dict[str, Any]) -> str:
    """Columna RUT en acta de reuniones (V)."""
    r = str(a.get("rut") or a.get("identification_number") or "").strip()
    return r if r else "—"


def attendee_phone_cell(a: Dict[str, Any]) -> str:
    """Columna teléfono en acta de reuniones (V), sin correo."""
    p = str(a.get("phone") or a.get("telefono") or "").strip()
    return p if p else "—"


def _row_to_dict(r: CourseActivityRowModel, section: Optional[str] = None) -> dict:
    sec = normalize_course_activity_section(section) if section is not None else "family"
    section_id = {"family": 1, "community": 2, "other": 3}[sec]
    return {
        "id": r.id,
        "course_id": r.course_id,
        "section": sec,
        "section_id": section_id,
        "date": r.date.isoformat() if r.date else None,
        "attendees": _load_attendees(r.attendees),
        "objectives": r.objectives,
        "activities": r.activities,
        "agreements": r.agreements,
        "results": r.results,
        "created_at": _date_str(r.created_at),
        "updated_at": _date_str(r.updated_at),
    }


class CourseActivityRecordClass:
    def __init__(self, db: Session):
        self.db = db

    def get_by_course_id(self, course_id: int, section: Optional[str] = None) -> Any:
        """Lista registros del curso, opcionalmente filtrados por section=family|community|other."""
        try:
            if section is not None and str(section).strip() != "":
                want = normalize_course_activity_section(section)
                Model = _model_for_section(want)
                rows = (
                    self.db.query(Model)
                    .filter(Model.course_id == course_id)
                    .order_by(Model.date.desc(), Model.id.desc())
                    .all()
                )
                return {"status": "success", "data": [_row_to_dict(r, want) for r in rows]}
            merged: List[tuple[str, CourseActivityRowModel]] = []
            for sec, Model in (
                ("family", CourseActivityFamilyModel),
                ("community", CourseActivityCommunityModel),
                ("other", CourseActivityOtherModel),
            ):
                for r in (
                    self.db.query(Model)
                    .filter(Model.course_id == course_id)
                    .all()
                ):
                    merged.append((sec, r))
            merged.sort(
                key=lambda t: (t[1].date or date.min, t[1].id or 0),
                reverse=True,
            )
            return {
                "status": "success",
                "data": [_row_to_dict(r, sec) for sec, r in merged],
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int, section: str) -> Any:
        try:
            Model = _model_for_section(section)
            want = normalize_course_activity_section(section)
            row = self.db.query(Model).filter(Model.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row, want)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        try:
            course_id = int(data.get("course_id"))
            sec = normalize_course_activity_section(data.get("section"))
            Model = _model_for_section(sec)
            date_val = _parse_date(data.get("date"))
            attendees = _parse_attendees(data.get("attendees"))
            objectives = (data.get("objectives") or "").strip() or None
            activities = (data.get("activities") or "").strip() or None
            agreements = (data.get("agreements") or "").strip() or None
            results = (data.get("results") or "").strip() or None
            now = datetime.now()

            row = Model(
                course_id=course_id,
                date=date_val,
                attendees=attendees,
                objectives=objectives,
                activities=activities,
                agreements=agreements,
                results=results,
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {
                "status": "success",
                "message": "Registro creado.",
                "id": row.id,
                "data": _row_to_dict(row, sec),
            }
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict, section: str) -> Any:
        try:
            Model = _model_for_section(section)
            want = normalize_course_activity_section(section)
            row = self.db.query(Model).filter(Model.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "date" in data:
                row.date = _parse_date(data.get("date"))
            if "attendees" in data:
                row.attendees = _parse_attendees(data.get("attendees"))
            if "objectives" in data:
                row.objectives = (data.get("objectives") or "").strip() or None
            if "activities" in data:
                row.activities = (data.get("activities") or "").strip() or None
            if "agreements" in data:
                row.agreements = (data.get("agreements") or "").strip() or None
            if "results" in data:
                row.results = (data.get("results") or "").strip() or None
            row.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(row)
            return {
                "status": "success",
                "message": "Registro actualizado.",
                "id": id,
                "data": _row_to_dict(row, want),
            }
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int, section: str) -> Any:
        try:
            Model = _model_for_section(section)
            row = self.db.query(Model).filter(Model.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            self.db.delete(row)
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado.", "id": id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
