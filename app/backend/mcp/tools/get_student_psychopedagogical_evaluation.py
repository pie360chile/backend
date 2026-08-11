"""Tool MCP: get_student_psychopedagogical_evaluation — lee doc 27 (o catalog) desde la ficha."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.backend.classes.agents_mcp_class import AgentsMcpClass
from app.backend.db.database import SessionLocal
from app.backend.mcp.auth import check_mcp_secret

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP") -> None:
    @mcp.tool()
    def get_student_psychopedagogical_evaluation(
        agent_id: str,
        customer_id: int,
        student_id: int,
        document_id: int = 27,
        secret: str = "",
    ) -> dict:
        """Obtiene el ÚLTIMO informe psicopedagógico desde la ficha del estudiante.

        Cuando Files del agente no tiene el psicopedagógico del caso, usa esta tool
        para leer el archivo más reciente subido en la carpeta/ficha del estudiante
        (document_id=27 por defecto). Si hay varias versiones, toma la última
        (por fecha de carga/actualización y version_id).

        Args:
            agent_id: UUID del agente PIE360.
            customer_id: Cliente dueño.
            student_id: Estudiante de la ficha.
            document_id: Tipo de documento en carpeta (default 27).
            secret: MCP_SECRET.
        """
        check_mcp_secret(secret)
        db = SessionLocal()
        try:
            result = AgentsMcpClass(db).get_student_psychopedagogical_evaluation(
                agent_id=agent_id,
                customer_id=int(customer_id),
                student_id=int(student_id),
                document_id=int(document_id) if document_id else 27,
            )
        finally:
            db.close()

        if result.get("status") == "error":
            raise ValueError(result.get("message") or "No se encontró el psicopedagógico en la ficha")
        return {
            "ok": True,
            "message": result.get("message"),
            **(result.get("data") or {}),
        }
