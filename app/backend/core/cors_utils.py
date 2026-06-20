"""Utilidades CORS."""

from __future__ import annotations

from app.backend.core.config import resolve_cors_origins, settings


def is_origin_allowed(origin: str | None) -> bool:
    if not origin:
        return False
    allowed, _ = resolve_cors_origins(settings.cors_origins)
    if "*" in allowed:
        return True
    return origin in allowed


def cors_headers_for_origin(origin: str | None) -> dict[str, str]:
    if not is_origin_allowed(origin):
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Vary": "Origin",
    }
