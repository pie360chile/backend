"""Compat: reexporta el MCP nuevo.

Preferir: `from app.backend.mcp import agents_mcp, get_mcp_asgi_app, MCP_HTTP_PATH`
"""

from __future__ import annotations

from app.backend.mcp.server import MCP_HTTP_PATH, agents_mcp, get_mcp_asgi_app

# Alias histórico usado por mcp_integration / imports viejos.
workspace_mcp = agents_mcp

__all__ = ["MCP_HTTP_PATH", "agents_mcp", "get_mcp_asgi_app", "workspace_mcp"]
