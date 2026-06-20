"""Monta el MCP del Workspace Agent dentro de la app FastAPI."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.backend.services.agent_workspace_mcp import get_mcp_asgi_app, workspace_mcp


def workspace_mcp_lifespan():
    """Context manager del session manager MCP (requerido por streamable HTTP)."""
    get_mcp_asgi_app()
    return workspace_mcp.session_manager.run()


@asynccontextmanager
async def combined_app_lifespan(app: FastAPI):
    async with workspace_mcp_lifespan():
        yield


def mount_workspace_mcp(app: FastAPI) -> None:
    """Expone MCP en http://host:puerto/mcp (mismo proceso que FastAPI)."""
    mcp_asgi = get_mcp_asgi_app()
    app.mount("/", mcp_asgi)
