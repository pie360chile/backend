"""Auth compartida para tools MCP de Agentes."""

from __future__ import annotations

from app.backend.core.config import settings


def check_mcp_secret(secret: str) -> None:
    """Valida el parámetro secret de las tools. Si MCP_SECRET está vacío, no exige auth."""
    expected = (settings.mcp_secret or "").strip()
    if not expected:
        return
    if (secret or "").strip() != expected:
        raise ValueError("Secret inválido.")
