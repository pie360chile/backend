"""Servidor FastMCP de Agentes (URL pública /api/mcp)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# FastAPI usa root_path=/api → ruta interna /mcp = URL pública /api/mcp
MCP_HTTP_PATH = "/mcp"

agents_mcp = FastMCP(
    name="PIE360 Agents MCP",
    stateless_http=True,
    streamable_http_path=MCP_HTTP_PATH,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
    instructions=(
        "PIE360 Agents MCP tools:\n"
        "1) create_document — genera Word/PDF con plantilla del agente, guarda en estudiante y rellena ficha.\n"
        "2) store_data — solo guarda campos pending (sin generar aún).\n"
        "3) search_agent_files — busca texto en archivos del agente (_derived/).\n"
        "Auth: parámetro secret = MCP_SECRET.\n"
        "Agregar tools en app/backend/mcp/tools/ (una por archivo)."
    ),
)


def get_mcp_asgi_app():
    """Starlette app del MCP (interno /mcp → público /api/mcp)."""
    # Import lazy: registra tools al cargar el paquete tools.
    from app.backend.mcp import tools as _tools  # noqa: F401

    _tools.register_tools(agents_mcp)
    return agents_mcp.streamable_http_app()
