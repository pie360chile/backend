"""Nombres y RUT de profesionales vía users (professionals.user_id)."""
from types import SimpleNamespace
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.backend.db.models import ProfessionalModel, UserModel


def professional_display_fields(db: Session, prof: Optional[ProfessionalModel]):
    """full_name, rut, email, phone desde users; career_type_id desde professionals."""
    empty = SimpleNamespace(full_name="", rut="", email="", phone="", career_type_id=None)
    if not prof:
        return empty
    uid = getattr(prof, "user_id", None)
    if uid:
        u = db.query(UserModel).filter(UserModel.id == uid).first()
        if u:
            return SimpleNamespace(
                full_name=(u.full_name or "").strip(),
                rut=(u.rut or "").strip(),
                email=(u.email or "").strip(),
                phone=(u.phone or "").strip(),
                career_type_id=getattr(prof, "career_type_id", None),
            )
    return empty


def professional_display_name(db: Session, professional_id: int) -> str:
    return map_professional_id_to_display_name(db, [professional_id]).get(
        int(professional_id), f"Profesional #{professional_id}"
    )


def map_professional_id_to_display_name(db: Session, pids: List[int]) -> Dict[int, str]:
    if not pids:
        return {}
    uniq = list({int(x) for x in pids if x is not None})
    rows = (
        db.query(ProfessionalModel.id, UserModel.full_name)
        .join(UserModel, ProfessionalModel.user_id == UserModel.id)
        .filter(ProfessionalModel.id.in_(uniq))
        .all()
    )
    out: Dict[int, str] = {}
    for rid, fn in rows:
        label = (fn or "").strip() or f"Profesional #{rid}"
        out[int(rid)] = label
    missing = set(uniq) - set(out.keys())
    for mid in missing:
        out[mid] = f"Profesional #{mid}"
    return out
