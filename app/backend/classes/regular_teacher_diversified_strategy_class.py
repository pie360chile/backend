import re
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from app.backend.db.models import RegularTeacherDiversifiedStrategyModel


def _normalize_period_from_payload(data: dict) -> Optional[str]:
    """period_id / periodId 1..3 → '1'..'3'. period puede ser número o texto (1er, 2do, …)."""
    for key in ("period_id", "periodId"):
        pid = data.get(key)
        if pid is not None:
            try:
                n = int(pid)
                if n in (1, 2, 3):
                    return str(n)
            except (TypeError, ValueError):
                pass
    p = data.get("period")
    if p is None:
        return None
    if isinstance(p, (int, float)):
        n = int(p)
        if n in (1, 2, 3):
            return str(n)
    s = str(p).strip()
    if not s:
        return None
    if s in ("1", "2", "3"):
        return s
    m = re.match(r"^\s*([123])\b", s)
    if m:
        return m.group(1)
    sl = s.lower()
    if sl.startswith(("1er", "1º", "primer")):
        return "1"
    if sl.startswith(("2do", "2º", "segund")):
        return "2"
    if sl.startswith(("3er", "3º", "tercer")):
        return "3"
    # No guardar texto libre en `period` (evita valores como "232" que rompen filtros y el Word).
    return None


def _period_synonyms(period_id: int) -> tuple[str, ...]:
    return {
        1: ("1", "1er", "1º", "primer", "primero", "i"),
        2: ("2", "2do", "2º", "segundo", "ii"),
        3: ("3", "3er", "3º", "tercer", "tercero", "iii"),
    }.get(period_id, (str(period_id),))


def _period_sql_filter(period_id: int):
    """Período 1 incluye filas sin period (legacy)."""
    pcol = RegularTeacherDiversifiedStrategyModel.period
    col = func.lower(func.trim(pcol))
    syn = _period_synonyms(period_id)
    match = or_(*[col == v.lower() for v in syn])
    if period_id == 1:
        legacy = or_(pcol.is_(None), pcol == "")
        return or_(match, legacy)
    return match


def _infer_period_id(period: Optional[str]) -> Optional[int]:
    if period is None:
        return None
    s = str(period).strip()
    if not s:
        return None
    if s in ("1", "2", "3"):
        return int(s)
    m = re.match(r"^\s*([123])\b", s)
    if m:
        return int(m.group(1))
    sl = s.lower()
    if sl.startswith(("1er", "1º", "primer")):
        return 1
    if sl.startswith(("2do", "2º", "segund")):
        return 2
    if sl.startswith(("3er", "3º", "tercer")):
        return 3
    return None


def _row_to_dict(r: RegularTeacherDiversifiedStrategyModel) -> dict:
    pid = _infer_period_id(r.period)
    if pid is None and (r.period is None or not str(r.period).strip()):
        pid = 1
    return {
        "id": r.id,
        "school_id": r.school_id,
        "course_id": r.course_id,
        "subject_id": r.subject_id,
        "strategy": r.strategy,
        "period": r.period,
        "period_id": pid,
        "criteria": r.criteria,
        "added_date": r.added_date.isoformat() if r.added_date else None,
        "updated_date": r.updated_date.isoformat() if r.updated_date else None,
    }


class RegularTeacherDiversifiedStrategyClass:
    def __init__(self, db: Session):
        self.db = db

    def get(
        self,
        school_id: Optional[int] = None,
        course_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        period_id: Optional[int] = None,
    ) -> Any:
        """Lista registros. Filtros opcionales por school_id, course_id, subject_id y period_id (1, 2 o 3)."""
        try:
            q = self.db.query(RegularTeacherDiversifiedStrategyModel)
            if school_id is not None and school_id != -1:
                q = q.filter(RegularTeacherDiversifiedStrategyModel.school_id == school_id)
            if course_id is not None and course_id != -1:
                q = q.filter(RegularTeacherDiversifiedStrategyModel.course_id == course_id)
            if subject_id is not None and subject_id != -1:
                q = q.filter(RegularTeacherDiversifiedStrategyModel.subject_id == subject_id)
            if period_id is not None and period_id in (1, 2, 3):
                q = q.filter(_period_sql_filter(period_id))
            rows = q.all()
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene un registro por id."""
        try:
            row = self.db.query(RegularTeacherDiversifiedStrategyModel).filter(RegularTeacherDiversifiedStrategyModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def get_by_course_id(self, course_id: int, period_id: Optional[int] = None) -> Any:
        """Obtiene registros por course_id; opcionalmente filtra por período (1, 2 o 3)."""
        try:
            q = self.db.query(RegularTeacherDiversifiedStrategyModel).filter(
                RegularTeacherDiversifiedStrategyModel.course_id == course_id
            )
            if period_id is not None and period_id in (1, 2, 3):
                q = q.filter(_period_sql_filter(period_id))
            rows = q.all()
            return {"status": "success", "data": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def store(self, data: dict) -> Any:
        """Crea un nuevo registro en regular_teacher_diversified_strategies. school_id del body o sesión."""
        try:
            now = datetime.now()
            row = RegularTeacherDiversifiedStrategyModel(
                school_id=data.get("school_id"),
                course_id=data.get("course_id"),
                subject_id=data.get("subject_id"),
                strategy=data.get("strategy"),
                period=_normalize_period_from_payload(data),
                criteria=data.get("criteria"),
                added_date=now,
                updated_date=now,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro creado.", "id": row.id, "data": _row_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza un registro por id; solo los campos enviados."""
        try:
            row = self.db.query(RegularTeacherDiversifiedStrategyModel).filter(RegularTeacherDiversifiedStrategyModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "school_id" in data:
                row.school_id = data["school_id"]
            if "course_id" in data:
                row.course_id = data["course_id"]
            if "subject_id" in data:
                row.subject_id = data["subject_id"]
            if "strategy" in data:
                row.strategy = data["strategy"]
            if "period_id" in data or "periodId" in data or "period" in data:
                merged = {
                    "period": data.get("period", row.period),
                    "period_id": data.get("period_id"),
                    "periodId": data.get("periodId"),
                }
                row.period = _normalize_period_from_payload(merged)
            if "criteria" in data:
                row.criteria = data["criteria"]
            row.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro actualizado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        """Elimina físicamente el registro."""
        try:
            row = self.db.query(RegularTeacherDiversifiedStrategyModel).filter(RegularTeacherDiversifiedStrategyModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            self.db.delete(row)
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
