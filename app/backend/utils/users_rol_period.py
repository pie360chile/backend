"""period_year en users_rols: año efectivo y filtros SQLAlchemy reutilizables."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import or_

from app.backend.db.models import UsersRolModel


def effective_period_year_int(period_year: Optional[Any]) -> int:
    """Si no viene año, usa el año calendario actual (comportamiento esperado en listados)."""
    if period_year is None:
        return datetime.now().year
    try:
        s = str(period_year).strip()
        return int(s) if s else datetime.now().year
    except (TypeError, ValueError):
        return datetime.now().year


def resolve_period_year_for_session(session_user, explicit_period_year: Optional[Any] = None) -> int:
    """Prioriza periodo explícito (body/query); si no, el del token/sesión; si no, año actual."""
    py = explicit_period_year
    if py is None and session_user is not None:
        py = getattr(session_user, "period_year", None)
    return effective_period_year_int(py)


def users_rol_period_clause(period_year: Optional[Any], *, bypass_global_rol_ids: tuple = (1,)):
    """
    Relación users_rols del período indicado.
    ``bypass_global_rol_ids``: filas con esos rol_id no se filtran por año (ej. superadmin 1).
    Usar ``bypass_global_rol_ids=()`` en listados que ya excluyen esos roles.
    """
    py = effective_period_year_int(period_year)
    if bypass_global_rol_ids:
        return or_(UsersRolModel.period_year == py, UsersRolModel.rol_id.in_(bypass_global_rol_ids))
    return UsersRolModel.period_year == py
