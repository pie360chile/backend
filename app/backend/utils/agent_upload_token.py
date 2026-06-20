"""Token firmado de un solo uso para subida multipart desde el sandbox del agente."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.backend.core.config import settings
from app.backend.utils.agent_workspace_storage import resolve_agent_id

_ALGORITHM = "HS256"
_UPLOAD_SCOPE = "workspace_agent_upload"
_DEFAULT_MINUTES = 15


def _signing_key() -> str:
    key = (settings.mcp_secret or settings.secret_key or "").strip()
    if not key:
        raise ValueError("MCP_SECRET o SECRET_KEY requerido para tokens de subida.")
    return key


def create_upload_token(filename: str, agent_id: str = "", minutes: int = _DEFAULT_MINUTES) -> str:
    aid = resolve_agent_id(agent_id)
    now = datetime.now(timezone.utc)
    payload = {
        "scope": _UPLOAD_SCOPE,
        "filename": filename.strip(),
        "agent_id": aid,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, _signing_key(), algorithm=_ALGORITHM)


def verify_upload_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _signing_key(), algorithms=[_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Token de subida inválido o expirado.") from exc
    if payload.get("scope") != _UPLOAD_SCOPE:
        raise ValueError("Token de subida inválido.")
    filename = (payload.get("filename") or "").strip()
    if not filename:
        raise ValueError("Token sin filename.")
    return {
        "filename": filename,
        "agent_id": resolve_agent_id(payload.get("agent_id")),
    }
