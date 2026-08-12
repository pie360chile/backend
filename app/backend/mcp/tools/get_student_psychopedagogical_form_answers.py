"""Tool MCP: get_student_psychopedagogical_form_answers — respuestas de Formularios PIE360."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.backend.classes.agents_mcp_class import AgentsMcpClass
from app.backend.db.database import SessionLocal
from app.backend.mcp.auth import check_mcp_secret

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP") -> None:
    @mcp.tool()
    def get_student_psychopedagogical_form_answers(
        agent_id: str,
        customer_id: int,
        student_id: int,
        school_id: int = 0,
        period_year: int = 0,
        secret: str = "",
    ) -> dict:
        """Obtiene respuestas del formulario de observación (Inf. Eval. Psicopedagógica).

        Cuando el cuestionario/Excel en Files del agente no trae la fila del estudiante,
        usa esta tool para leer las respuestas guardadas en PIE360 → Formularios
        (dynamic_forms / dynamic_form_submissions) y redactar el informe con esa evidencia.

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
            result = AgentsMcpClass(db).get_student_psychopedagogical_form_answers(
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
                result.get("message") or "No hay respuestas de formulario para el estudiante"
            )
        return {
            "ok": True,
            "message": result.get("message"),
            **(result.get("data") or {}),
        }
