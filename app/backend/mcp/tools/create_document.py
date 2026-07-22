"""Tool MCP: create_document — genera Word/PDF con la plantilla del agente."""

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
    def create_document(
        agent_id: str,
        customer_id: int,
        student_id: int,
        document_id: int,
        fields_json: str,
        meta_json: str = "",
        secret: str = "",
    ) -> dict:
        """Genera el documento con la plantilla del agente para ese document_id.

        La plantilla se carga en Agente → Documentos y queda asociada a:
        - un tipo de documento PIE360 (document_id)
        - su formulario (al generar se rellena la ficha correspondiente)

        Args:
            agent_id: UUID del agente PIE360.
            customer_id: Cliente dueño.
            student_id: Estudiante destino.
            document_id: Tipo de documento (= plantilla + formulario).
            fields_json: JSON {nombre_campo: valor} de esa plantilla.
            meta_json: Metadatos opcionales.
            secret: MCP_SECRET.
        """
        check_mcp_secret(secret)
        try:
            fields = json.loads(fields_json) if fields_json.strip() else {}
        except json.JSONDecodeError as exc:
            raise ValueError(f"fields_json no es JSON válido: {exc}") from exc
        if not isinstance(fields, dict) or not fields:
            raise ValueError("fields_json debe ser un objeto con al menos un campo.")

        meta: dict = {}
        if meta_json and meta_json.strip():
            try:
                parsed = json.loads(meta_json)
            except json.JSONDecodeError as exc:
                raise ValueError(f"meta_json no es JSON válido: {exc}") from exc
            if not isinstance(parsed, dict):
                raise ValueError("meta_json debe ser un objeto JSON.")
            meta = parsed

        db = SessionLocal()
        try:
            result = AgentsMcpClass(db).create_document(
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
            raise ValueError(result.get("message") or "Error en create_document")
        data = result.get("data") or {}
        return {
            "ok": True,
            "message": result.get("message"),
            "save": data.get("save"),
            "responseFiles": data.get("responseFiles") or [],
            "formFilled": bool(data.get("formFilled")),
        }
