"""MCP de Agentes PIE360.

Estructura:

  mcp/
    auth.py
    server.py
    tools/               # una tool por archivo
      create_document.py
      store_data.py
      search_agent_files.py

Negocio en classes/agents_mcp_class.py.
Docs: backend/docs/agents_mcp.md
"""

from app.backend.mcp.server import MCP_HTTP_PATH, get_mcp_asgi_app, agents_mcp

__all__ = ["MCP_HTTP_PATH", "agents_mcp", "get_mcp_asgi_app"]
