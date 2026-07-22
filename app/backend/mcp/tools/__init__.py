"""Registro de tools MCP. Una tool = un módulo en este paquete."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

_registered = False


def register_tools(mcp: "FastMCP") -> None:
    """Idempotente: registra todas las tools en el servidor FastMCP."""
    global _registered
    if _registered:
        return

    from app.backend.mcp.tools import create_document, search_agent_files, store_data

    create_document.register(mcp)
    store_data.register(mcp)
    search_agent_files.register(mcp)

    _registered = True
