"""Monta el MCP de Agentes dentro de la app FastAPI."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.routing import Route

from app.backend.mcp import MCP_HTTP_PATH, agents_mcp, get_mcp_asgi_app
from app.backend.utils.student_drive_sync_worker import run_student_drive_sync_worker

# Ruta interna (con root_path=/api la URL pública es /api/mcp)
MCP_PUBLIC_PATH = MCP_HTTP_PATH


def workspace_mcp_lifespan():
    """Context manager del session manager MCP (requerido por streamable HTTP)."""
    get_mcp_asgi_app()
    return agents_mcp.session_manager.run()


@asynccontextmanager
async def combined_app_lifespan(app: FastAPI):
    stop_drive_worker = asyncio.Event()
    drive_worker = asyncio.create_task(
        run_student_drive_sync_worker(stop_drive_worker),
        name="student-drive-sync-worker",
    )
    async with workspace_mcp_lifespan():
        try:
            yield
        finally:
            stop_drive_worker.set()
            try:
                await asyncio.wait_for(drive_worker, timeout=10)
            except asyncio.TimeoutError:
                drive_worker.cancel()


def mount_workspace_mcp(app: FastAPI) -> None:
    """Registra MCP en /api/mcp (mismo proceso que FastAPI)."""
    mcp_asgi = get_mcp_asgi_app()
    for route in mcp_asgi.routes:
        if not isinstance(route, Route):
            continue
        app.router.routes.append(
            Route(
                MCP_PUBLIC_PATH,
                endpoint=route.endpoint,
                methods=["GET", "POST", "DELETE", "OPTIONS"],
            )
        )
