"""MCP del Workspace Agent — guardar análisis JSON y store_data de agentes."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.backend.classes.agents_mcp_class import AgentsMcpClass
from app.backend.core.config import settings
from app.backend.db.database import SessionLocal
from app.backend.utils import agent_workspace_storage as storage
from app.backend.utils.agent_analisis_validation import validate_analisis_payload

# FastAPI usa root_path=/api → ruta interna /mcp = URL pública /api/mcp
MCP_HTTP_PATH = "/mcp"

workspace_mcp = FastMCP(
    name="PIE360 Agent Storage",
    stateless_http=True,
    streamable_http_path=MCP_HTTP_PATH,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
    instructions=(
        "PIE360 MCP tools:\n"
        "1) save_agent_analisis_json — guarda informe JSON legado en files/agents/.\n"
        "2) store_data — guarda campos de plantilla del agente (agents_mcp_saves, origin=agent). "
        "Luego el chat de Agentes genera el Word/PDF.\n"
        "Auth en ambas: parámetro secret = MCP_SECRET.\n"
        "Word (.docx) vía plantillas del agente. Nunca PDF como entrega final del análisis legado."
    ),
)


def _check_secret(secret: str) -> None:
    if not settings.mcp_secret:
        return
    if secret and secret != settings.mcp_secret:
        raise ValueError("Secret inválido.")


@workspace_mcp.tool()
def save_agent_analisis_json(
    filename: str,
    payload_json: str,
    agent_id: str = "",
    secret: str = "",
) -> dict:
    """Guarda el análisis/redacción del informe como JSON en files/agents/{agent_id}/.

    El JSON es espejo fiel del Word: cada valor en secciones debe ser el texto COMPLETO
    del cuadro correspondiente, palabra por palabra, sin resúmenes ni '...'.

    Esquema recomendado (familia):
    {
      "tipo_informe": "familia",
      "estudiante": {"nombre": "...", "curso": "...", "establecimiento": "..."},
      "docx_filename": "InformeFamilia_2E-NOMBRE APELLIDO.docx",
      "drive_folder": "PIE360 Informes",
      "generado_en": "2026-06-20",
      "secciones": {
        "diagnostico": "texto completo del cuadro",
        "resultados_evaluacion": "párrafo completo",
        "instrumentos_aplicados": ["viñeta 1", "viñeta 2"],
        "ambito_pedagogico": "párrafo completo fortalezas y necesidades",
        "ambito_social_afectivo": "párrafo completo",
        "trabajo_colaborativo": "párrafo completo",
        "apoyos_hogar": "párrafo completo",
        "acuerdos": ["compromiso escuela...", "compromiso familia...", "compromiso compartido..."],
        "fechas_avances": ["Junio 2026", "Dic. 2026", "Junio 2027", "Dic. 2027"]
      }
    }

    La respuesta incluye ok, filename, size_bytes y path si el guardado fue exitoso.
    """
    _check_secret(secret)
    if not payload_json.strip():
        raise ValueError("payload_json no puede estar vacío.")
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"payload_json no es JSON válido: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("payload_json debe ser un objeto JSON (dict).")
    validate_analisis_payload(payload)
    aid = storage.resolve_agent_id(agent_id)
    result = storage.save_json_payload(aid, filename, payload)
    result["keys"] = list(payload.keys())
    return result


@workspace_mcp.tool()
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
        document_id: ID del documento/plantilla (mismo que en agents_document_templates).
        fields_json: JSON objeto {nombre_campo: valor} alineado a detected_fields.
        meta_json: JSON objeto opcional con metadatos.
        secret: MCP_SECRET (mismo que en el connector ChatGPT).

    Ejemplo fields_json:
    {"diagnostico": "texto…", "resultados_evaluacion": "texto…"}
    """
    _check_secret(secret)
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


def get_mcp_asgi_app():
    """Starlette app del MCP (interno /mcp → público /api/mcp)."""
    return workspace_mcp.streamable_http_app()
