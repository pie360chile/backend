"""Utilidades CORS para el frontend del agente en Firebase."""

from __future__ import annotations

import re

from app.backend.core.config import resolve_cors_origins, settings

_AGENT_ORIGIN_RE = re.compile(
    r"^https://agent-[a-z0-9-]+\.(web\.app|firebaseapp\.com)$",
    re.IGNORECASE,
)


def is_origin_allowed(origin: str | None) -> bool:
    if not origin:
        return False
    allowed, _ = resolve_cors_origins(settings.cors_origins)
    if origin in allowed:
        return True
    return bool(_AGENT_ORIGIN_RE.match(origin))


def cors_headers_for_origin(origin: str | None) -> dict[str, str]:
    if not is_origin_allowed(origin):
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Vary": "Origin",
    }
