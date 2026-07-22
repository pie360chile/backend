"""Tool MCP: search_agent_files — retrieval barato sobre _derived/ del agente."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.backend.classes.agents_mcp_class import AgentsMcpClass
from app.backend.db.database import SessionLocal
from app.backend.mcp.auth import check_mcp_secret

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP") -> None:
    @mcp.tool()
    def search_agent_files(
        agent_id: str,
        customer_id: int,
        query: str,
        student_rut: str = "",
        secret: str = "",
    ) -> dict:
        """Busca trozos relevantes en los archivos del agente (texto derivado).

        Usa el índice _derived/ (sin embeddings de pago). Ideal cuando necesitas
        datos de Excel/PDF/Word del agente sin cargar todo el archivo al prompt.

        Args:
            agent_id: UUID del agente PIE360.
            customer_id: ID del cliente dueño del agente.
            query: Pregunta o palabras clave (ej. "diagnóstico", nombre, RUT).
            student_rut: RUT opcional para priorizar filas de planillas.
            secret: MCP_SECRET.
        """
        check_mcp_secret(secret)
        db = SessionLocal()
        try:
            result = AgentsMcpClass(db).search_agent_files(
                agent_id=agent_id,
                customer_id=int(customer_id),
                query=query or "",
                student_rut=(student_rut or "").strip() or None,
            )
        finally:
            db.close()

        if result.get("status") == "error":
            raise ValueError(result.get("message") or "Error en search_agent_files")
        return {
            "ok": True,
            "message": result.get("message"),
            **(result.get("data") or {}),
        }
