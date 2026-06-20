"""Monta el MCP del Workspace Agent dentro de la app FastAPI."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.routing import Route

from app.backend.services.agent_workspace_mcp import (
    MCP_HTTP_PATH,
    get_mcp_asgi_app,
    workspace_mcp,
)

# Ruta interna (con root_path=/api la URL pública es /api/mcp)
MCP_PUBLIC_PATH = MCP_HTTP_PATH


def workspace_mcp_lifespan():
    """Context manager del session manager MCP (requerido por streamable HTTP)."""
    get_mcp_asgi_app()
    return workspace_mcp.session_manager.run()


@asynccontextmanager
async def combined_app_lifespan(app: FastAPI):
    async with workspace_mcp_lifespan():
        yield


def mount_workspace_mcp(app: FastAPI) -> None:
    """Registra MCP en /api/mcp (mismo proceso que FastAPI)."""
    mcp_asgi = get_mcp_asgi_app()
    for route in mcp_asgi.routes:
        if not isinstance(route, Route):
            continue
        # add_route de FastAPI no sirve para ASGI apps; usar Route de Starlette.
        app.router.routes.append(
            Route(
                MCP_PUBLIC_PATH,
                endpoint=route.endpoint,
                methods=["GET", "POST", "DELETE", "OPTIONS"],
            )
        )
