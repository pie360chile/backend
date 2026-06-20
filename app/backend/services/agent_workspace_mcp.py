"""MCP del Workspace Agent — herramientas para guardar informes en files/agents/."""

from __future__ import annotations

import base64
import re

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.backend.core.config import settings
from app.backend.utils import agent_workspace_storage as storage

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
        "Guarda informes generados (PDF, Word) en el servidor PIE360. "
        "Para archivos pequeños: save_agent_pdf o save_agent_docx. "
        "Para archivos grandes: begin_agent_file_upload, append_agent_file_chunk, "
        "finalize_agent_file_upload (chunks de ~256 KB en base64)."
    ),
)


def _check_secret(secret: str) -> None:
    if not settings.mcp_secret:
        return
    if secret and secret != settings.mcp_secret:
        raise ValueError("Secret inválido.")


def _ensure_extension(filename: str, ext: str) -> str:
    name = filename.strip()
    if not name.lower().endswith(ext):
        return f"{name}{ext}"
    return name


@workspace_mcp.tool()
def save_agent_pdf(
    filename: str,
    pdf_base64: str,
    agent_id: str = "",
    secret: str = "",
) -> dict:
    """Guarda un PDF en files/agents/{agent_id}/. Para PDFs grandes usa subida por chunks."""
    _check_secret(secret)
    aid = storage.resolve_agent_id(agent_id)
    fname = _ensure_extension(filename, ".pdf")
    data = base64.b64decode(pdf_base64, validate=True)
    path = storage.target_file(aid, fname)
    path.write_bytes(data)
    return storage.file_result(path, aid, fname)


@workspace_mcp.tool()
def save_agent_docx(
    filename: str,
    docx_base64: str,
    agent_id: str = "",
    secret: str = "",
) -> dict:
    """Guarda un Word (.docx) en files/agents/{agent_id}/. Para archivos grandes usa subida por chunks."""
    _check_secret(secret)
    aid = storage.resolve_agent_id(agent_id)
    fname = _ensure_extension(filename, ".docx")
    data = base64.b64decode(docx_base64, validate=True)
    path = storage.target_file(aid, fname)
    path.write_bytes(data)
    return storage.file_result(path, aid, fname)


@workspace_mcp.tool()
def begin_agent_file_upload(
    filename: str,
    total_chunks: int,
    agent_id: str = "",
    secret: str = "",
) -> dict:
    """Inicia subida por partes. Divide el archivo en chunks de ~256 KB (crudo) antes de codificar en base64."""
    _check_secret(secret)
    return storage.begin_chunked_upload(agent_id, filename, total_chunks)


@workspace_mcp.tool()
def append_agent_file_chunk(
    upload_id: str,
    chunk_index: int,
    chunk_base64: str,
    agent_id: str = "",
    secret: str = "",
) -> dict:
    """Envía un fragmento de la subida. chunk_index empieza en 0."""
    _check_secret(secret)
    data = base64.b64decode(chunk_base64, validate=True)
    return storage.append_upload_chunk(agent_id, upload_id, chunk_index, data)


@workspace_mcp.tool()
def finalize_agent_file_upload(
    upload_id: str,
    agent_id: str = "",
    secret: str = "",
) -> dict:
    """Ensambla todos los chunks y guarda el archivo final en files/agents/{agent_id}/."""
    _check_secret(secret)
    return storage.finalize_chunked_upload(agent_id, upload_id)


@workspace_mcp.tool()
def cancel_agent_file_upload(
    upload_id: str,
    agent_id: str = "",
    secret: str = "",
) -> dict:
    """Cancela una subida por partes y elimina los chunks temporales."""
    _check_secret(secret)
    return storage.cancel_chunked_upload(agent_id, upload_id)


@workspace_mcp.tool()
def save_informe_texto(
    nombre: str,
    contenido_texto: str,
    tipo_informe: str = "",
    agent_id: str = "",
    secret: str = "",
) -> dict:
    """Guarda el escrito completo del informe como .txt en files/agents/{agent_id}/."""
    _check_secret(secret)
    if not contenido_texto.strip():
        raise ValueError("contenido_texto no puede estar vacío.")

    aid = storage.resolve_agent_id(agent_id)
    base = re.sub(r"\.(txt|md)$", "", nombre.strip(), flags=re.IGNORECASE)
    fname = f"{base}.txt"
    path = storage.target_file(aid, fname)
    header = f"# {base}\n"
    if tipo_informe:
        header += f"# tipo: {tipo_informe}\n"
    path.write_text(header + "\n" + contenido_texto, encoding="utf-8")
    result = storage.file_result(path, aid, fname)
    result["tipo_informe"] = tipo_informe
    return result


@workspace_mcp.tool()
def save_informe_complete(
    nombre: str,
    contenido_texto: str,
    pdf_base64: str,
    tipo_informe: str = "",
    agent_id: str = "",
    secret: str = "",
) -> dict:
    """Guarda texto + PDF del informe en files/agents/{agent_id}/."""
    _check_secret(secret)
    aid = storage.resolve_agent_id(agent_id)
    texto = save_informe_texto(
        nombre=nombre,
        contenido_texto=contenido_texto,
        tipo_informe=tipo_informe,
        agent_id=aid,
        secret=secret,
    )
    pdf_name = nombre if nombre.lower().endswith(".pdf") else f"{nombre}.pdf"
    pdf = save_agent_pdf(
        filename=pdf_name,
        pdf_base64=pdf_base64,
        agent_id=aid,
        secret=secret,
    )
    return {"ok": True, "agent_id": aid, "texto": texto, "pdf": pdf}


@workspace_mcp.tool()
def save_informe_docx_complete(
    nombre: str,
    contenido_texto: str,
    docx_base64: str,
    tipo_informe: str = "",
    agent_id: str = "",
    secret: str = "",
) -> dict:
    """Guarda texto + Word (.docx) del informe en files/agents/{agent_id}/."""
    _check_secret(secret)
    aid = storage.resolve_agent_id(agent_id)
    texto = save_informe_texto(
        nombre=nombre,
        contenido_texto=contenido_texto,
        tipo_informe=tipo_informe,
        agent_id=aid,
        secret=secret,
    )
    docx_name = nombre if nombre.lower().endswith(".docx") else f"{nombre}.docx"
    docx = save_agent_docx(
        filename=docx_name,
        docx_base64=docx_base64,
        agent_id=aid,
        secret=secret,
    )
    return {"ok": True, "agent_id": aid, "texto": texto, "docx": docx}


@workspace_mcp.tool()
def list_agent_files(agent_id: str = "", secret: str = "") -> dict:
    """Lista archivos guardados en files/agents/{agent_id}/."""
    _check_secret(secret)
    aid = storage.resolve_agent_id(agent_id)
    folder = storage.agent_folder(aid)
    files = [
        {
            "name": item.name,
            "path": str(item),
            "size_bytes": item.stat().st_size,
        }
        for item in sorted(folder.iterdir())
        if item.is_file()
    ]
    return {"ok": True, "agent_id": aid, "folder": str(folder), "files": files}


@workspace_mcp.tool()
def get_default_agent_id(secret: str = "") -> dict:
    """Devuelve el agent_id configurado (WORKSPACE_AGENT_ID)."""
    _check_secret(secret)
    return {"ok": True, "agent_id": storage.default_agent_id()}


def get_mcp_asgi_app():
    """Starlette app del MCP (interno /mcp → público /api/mcp)."""
    return workspace_mcp.streamable_http_app()
