"""Filtros por año de período escolar (period_year) en consultas SQLAlchemy."""

from __future__ import annotations

from typing import Any, Optional, Type

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Query as SAQuery


def apply_period_year_filter(query: SAQuery, model: Type[Any], period_year: Optional[int]) -> SAQuery:
    """
    Aplica filtro `model.period_year == period_year` si el modelo tiene la columna y se pasó año.

    - Columnas `Integer`: comparación numérica.
    - Columnas `String` (ej. students/professionals): comparación con str(period_year).
    """
    if period_year is None:
        return query
    try:
        mapper = sa_inspect(model)
    except Exception:
        return query
    if "period_year" not in mapper.columns:
        return query
    col = getattr(model, "period_year")
    col_type = mapper.columns["period_year"].type
    python_type = getattr(col_type, "python_type", None)
    if python_type is str:
        return query.filter(col == str(period_year).strip())
    try:
        py_int = int(period_year)
    except (TypeError, ValueError):
        return query
    return query.filter(col == py_int)
