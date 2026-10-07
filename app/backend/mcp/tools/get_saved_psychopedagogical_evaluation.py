"""Tool MCP: get_saved_psychopedagogical_evaluation — ficha guardada en la BD."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.backend.classes.agents_mcp_class import AgentsMcpClass
from app.backend.db.database import SessionLocal
from app.backend.mcp.auth import check_mcp_secret

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP") -> None:
    @mcp.tool()
    def get_saved_psychopedagogical_evaluation(
        agent_id: str,
        customer_id: int,
        student_id: int,
        secret: str = "",
    ) -> dict:
        """Lee el informe psicopedagógico guardado en la base de PIE360.

        Al generar el psicopedagógico, los textos quedan en
        psychopedagogical_evaluation_info. El Informe a la Familia debe usar
        esta tool siempre: trae diagnóstico, instrumentos, análisis, síntesis,
        conclusión y sugerencias de esa ficha. No la reemplaces por otros RUT.

        Args:
            agent_id: UUID del agente PIE360.
            customer_id: Cliente dueño.
            student_id: Estudiante.
            secret: MCP_SECRET.
        """
        check_mcp_secret(secret)
        db = SessionLocal()
        try:
            result = AgentsMcpClass(db).get_saved_psychopedagogical_evaluation(
                agent_id=agent_id,
                customer_id=int(customer_id),
                student_id=int(student_id),
            )
        finally:
            db.close()

        if result.get("status") == "error":
            raise ValueError(
                result.get("message") or "No hay informe psicopedagógico guardado"
            )
        return {
            "ok": True,
            "message": result.get("message"),
            **(result.get("data") or {}),
        }
