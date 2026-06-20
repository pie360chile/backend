"""MCP del Workspace Agent — guardar análisis JSON en files/agents/."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.backend.core.config import settings
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
        "PIE360: save_agent_analisis_json guarda el informe como JSON. "
        "secciones debe contener el TEXTO INTEGRO de cada cuadro del Word (mismas palabras), "
        "nunca resúmenes ni extractos con '...'. "
        "Word (.docx): Google Drive. Nunca PDF como entrega final."
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


def get_mcp_asgi_app():
    """Starlette app del MCP (interno /mcp → público /api/mcp)."""
    return workspace_mcp.streamable_http_app()
