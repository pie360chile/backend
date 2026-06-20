from __future__ import annotations

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile, status

from app.backend.classes.workspace_agent_class import WorkspaceAgentClass
from app.backend.core.config import settings
from app.backend.core.responses import api_error, api_response
from app.backend.schemas.workspace_agent import WorkspaceChatRequest
from app.backend.utils.agent_upload_token import verify_upload_token

workspace_agent = APIRouter(
    prefix="/workspace-agent",
    tags=["WorkspaceAgent"],
)


def _require_mcp_secret(
    authorization: str | None = None,
    x_mcp_secret: str | None = None,
) -> None:
    if not settings.mcp_secret:
        return
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_mcp_secret:
        token = x_mcp_secret.strip()
    if token != settings.mcp_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Secret inválido")


@workspace_agent.post("/chat")
    result = WorkspaceAgentClass().trigger_chat(body.input)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_502_BAD_GATEWAY),
            message=result.get("message", "Error"),
            data=result.get("data"),
        )
    return api_response(
        status_code=status.HTTP_200_OK,
        message=result.get("message", "OK"),
        data=result.get("data"),
    )


@workspace_agent.get("/agents")
def list_workspace_agents():
    result = WorkspaceAgentClass().list_agents()
    return api_response(data=result.get("data", []))


@workspace_agent.get("/agents/{agent_id}/files")
def list_workspace_agent_files(agent_id: str):
    result = WorkspaceAgentClass().list_files(agent_id)
    return api_response(data=result.get("data"))


@workspace_agent.post("/files/upload")
async def upload_workspace_agent_file(
    file: UploadFile = File(...),
    filename: str = Form(""),
    agent_id: str = Form(""),
    token: str = Query(""),
    authorization: str | None = Header(default=None),
    x_mcp_secret: str | None = Header(default=None),
):
    """Subida multipart de .docx. Auth: Bearer MCP_SECRET o ?token= (firmado por prepare_docx_upload)."""
    resolved_agent_id = agent_id or None
    resolved_filename = (filename or file.filename or "").strip()

    if token:
        try:
            claims = verify_upload_token(token)
        except ValueError as exc:
            return api_error(status_code=status.HTTP_401_UNAUTHORIZED, message=str(exc))
        resolved_agent_id = claims["agent_id"]
        if not resolved_filename:
            resolved_filename = claims["filename"]
        elif _safe_upload_name(resolved_filename) != claims["filename"]:
            return api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="filename no coincide con el token de subida.",
            )
    else:
        try:
            _require_mcp_secret(authorization, x_mcp_secret)
        except HTTPException as exc:
            return api_error(status_code=exc.status_code, message=str(exc.detail))

    data = await file.read()
    result = WorkspaceAgentClass().upload_file(resolved_filename, data, resolved_agent_id)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


def _safe_upload_name(value: str) -> str:
    from app.backend.utils.agent_workspace_storage import _safe_segment

    return _safe_segment(value.strip())
