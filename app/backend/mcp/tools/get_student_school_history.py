"""Tool MCP: get_student_school_history — anamnesis y formulario del apoderado."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.backend.classes.agents_mcp_class import AgentsMcpClass
from app.backend.db.database import SessionLocal
from app.backend.mcp.auth import check_mcp_secret

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP") -> None:
    @mcp.tool()
    def get_student_school_history(
        agent_id: str,
        customer_id: int,
        student_id: int,
        school_id: int = 0,
        period_year: int = 0,
        secret: str = "",
    ) -> dict:
        """Lee la anamnesis y el formulario del apoderado para la historia escolar.

        Úsala para redactar el apartado de antecedentes relevantes sobre la historia
        escolar. Trae la anamnesis (jardín, repitencia, colegios, apoyo familiar,
        medicación si está indicada) y las respuestas del formulario del apoderado.
        No inventes hechos que esta tool no devuelva.

        Args:
            agent_id: UUID del agente PIE360.
            customer_id: Cliente dueño.
            student_id: Estudiante.
            school_id: Colegio (0 = resolver desde el estudiante).
            period_year: Año del período (0 = sin filtrar).
            secret: MCP_SECRET.
        """
        check_mcp_secret(secret)
        db = SessionLocal()
        try:
            result = AgentsMcpClass(db).get_student_school_history(
                agent_id=agent_id,
                customer_id=int(customer_id),
                student_id=int(student_id),
                school_id=int(school_id) if school_id and int(school_id) > 0 else None,
                period_year=int(period_year) if period_year and int(period_year) > 0 else None,
            )
        finally:
            db.close()

        if result.get("status") == "error":
            raise ValueError(
                result.get("message") or "No hay historia escolar para el estudiante"
            )
        return {
            "ok": True,
            "message": result.get("message"),
            **(result.get("data") or {}),
        }
