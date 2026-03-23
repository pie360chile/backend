"""Dependencias FastAPI reutilizables para period_year (query string)."""

from typing import Optional

from fastapi import Query


def optional_period_year(
    period_year: Optional[int] = Query(
        None,
        ge=2000,
        le=2100,
        description="Año del período escolar (enviado por el front vía interceptor axios)",
    ),
) -> Optional[int]:
    return period_year


def required_period_year(
    period_year: int = Query(
        ...,
        ge=2000,
        le=2100,
        description="Año del período escolar (obligatorio)",
    ),
) -> int:
    return period_year
