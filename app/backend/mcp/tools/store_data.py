"""Tool MCP: store_data — persiste campos de plantilla del agente."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.backend.classes.agents_mcp_class import AgentsMcpClass
from app.backend.db.database import SessionLocal
from app.backend.mcp.auth import check_mcp_secret

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP") -> None:
    @mcp.tool()
    def store_data(
        agent_id: str,
        customer_id: int,
        student_id: int,
        document_id: int,
        fields_json: str,
        meta_json: str = "",
        secret: str = "",
    ) -> dict:
        """Guarda campos de la plantilla del agente (origin=agent, status=pending).

        El chat de Agentes (panel) hace poll y genera el Word/PDF con generate.

        Args:
            agent_id: UUID del agente PIE360.
            customer_id: ID del cliente dueño del agente.
            student_id: ID del estudiante.
            document_id: ID del documento/plantilla (agents_document_templates).
            fields_json: JSON objeto {nombre_campo: valor} alineado a detected_fields.
            meta_json: JSON objeto opcional con metadatos.
            secret: MCP_SECRET.
        """
        check_mcp_secret(secret)
        try:
            fields = json.loads(fields_json) if fields_json.strip() else {}
        except json.JSONDecodeError as exc:
            raise ValueError(f"fields_json no es JSON válido: {exc}") from exc
        if not isinstance(fields, dict):
            raise ValueError("fields_json debe ser un objeto JSON.")

        meta: dict = {}
        if meta_json and meta_json.strip():
            try:
                parsed_meta = json.loads(meta_json)
            except json.JSONDecodeError as exc:
                raise ValueError(f"meta_json no es JSON válido: {exc}") from exc
            if not isinstance(parsed_meta, dict):
                raise ValueError("meta_json debe ser un objeto JSON.")
            meta = parsed_meta

        db = SessionLocal()
        try:
            result = AgentsMcpClass(db).store_data(
                agent_id=agent_id,
                customer_id=int(customer_id),
                student_id=int(student_id),
                document_id=int(document_id),
                fields=fields,
                meta=meta,
            )
        finally:
            db.close()

        if result.get("status") == "error":
            raise ValueError(result.get("message") or "Error en store_data")
        return {
            "ok": True,
            "message": result.get("message"),
            "save": result.get("data"),
        }
