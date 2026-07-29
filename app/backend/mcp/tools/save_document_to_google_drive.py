"""Tool MCP: save_document_to_google_drive — sube el documento al árbol del colegio."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.backend.classes.agents_mcp_class import AgentsMcpClass
from app.backend.db.database import SessionLocal
from app.backend.mcp.auth import check_mcp_secret

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP") -> None:
    @mcp.tool()
    def save_document_to_google_drive(
        agent_id: str,
        customer_id: int,
        student_id: int,
        document_id: int,
        save_id: int = 0,
        file_name: str = "",
        secret: str = "",
    ) -> dict:
        """Sube un documento ya generado a Google Drive del cliente.

        Árbol (crea carpetas si no existen):
          Nombre del liceo / Año / Curso / RUT numérico del alumno / archivo

        Nombre del archivo siempre:
          {RUT_numerico}_{Tipo de documento}.{ext}
          Ejemplo: 274309032_Informe a la Familia.docx

        Normalmente create_document ya sube a Drive al generar. Usa esta tool
        para reintentar o subir de nuevo un save_id concreto.

        Args:
            agent_id: UUID del agente PIE360.
            customer_id: Cliente dueño (Drive de ese customer).
            student_id: Estudiante.
            document_id: Tipo de documento del catálogo.
            save_id: ID del save generado (recomendado). Si 0, usa file_name.
            file_name: Nombre del archivo en system/students (alternativa a save_id).
            secret: MCP_SECRET.
        """
        check_mcp_secret(secret)
        db = SessionLocal()
        try:
            result = AgentsMcpClass(db).save_document_to_google_drive(
                agent_id=agent_id,
                customer_id=int(customer_id),
                student_id=int(student_id),
                document_id=int(document_id),
                save_id=int(save_id) if int(save_id or 0) > 0 else None,
                file_name=(file_name or "").strip() or None,
            )
        finally:
            db.close()

        if result.get("status") == "error":
            raise ValueError(result.get("message") or "Error al subir a Google Drive")
        data = result.get("data") or {}
        return {
            "ok": True,
            "message": result.get("message"),
            "drive_path": data.get("drive_path"),
            "web_view_link": data.get("web_view_link"),
            "filename": data.get("filename"),
            "replaced": data.get("replaced"),
            "googleDrive": data,
        }
