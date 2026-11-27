"""Alcance de sesión para totales / listados (superadmin vs administrador de cliente)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.backend.db.models import RolModel


def is_superadmin_role(session_user) -> bool:
    return int(getattr(session_user, "rol_id", 0) or 0) == 1


def is_customer_admin_role(session_user, db: Session) -> bool:
    """Administrador global (rol_id=2) o Administrador por colegio (nombre)."""
    rid = int(getattr(session_user, "rol_id", 0) or 0)
    if rid == 1:
        return False
    if rid == 2:
        return True
    try:
        row = db.query(RolModel).filter(RolModel.id == rid).first()
        name = (getattr(row, "rol", None) or "").lower()
        return "administrador" in name and "super" not in name
    except Exception:
        return False


def resolve_totals_scope(session_user, db: Session):
    """
    Normaliza customer_id / school_id / rol_id para endpoints /totals.
    Admin de establecimiento (cualquier rol Administrador) → totales del customer (rol_id efectivo 2).
    """
    customer_id = getattr(session_user, "customer_id", None) if session_user else None
    school_id = getattr(session_user, "school_id", None) if session_user else None
    rol_id = getattr(session_user, "rol_id", None) if session_user else None

    if is_customer_admin_role(session_user, db) and customer_id:
        return customer_id, None, 2
    if is_superadmin_role(session_user):
        return customer_id, school_id, 1
    return customer_id, school_id, rol_id
