from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status

from app.backend.classes.workspace_agent_class import WorkspaceAgentClass
from app.backend.core.config import settings
from app.backend.core.responses import api_error, api_response
from app.backend.schemas.workspace_agent import WorkspaceChatRequest

workspace_agent = APIRouter(
    prefix="/workspace-agent",
    tags=["WorkspaceAgent"],
)


def _require_mcp_secret(
    authorization: str | None = Header(default=None),
    x_mcp_secret: str | None = Header(default=None),
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
def trigger_workspace_agent_chat(body: WorkspaceChatRequest):
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
    _: None = Depends(_require_mcp_secret),
):
    """Subida multipart de PDF/Word (alternativa a base64 en MCP). Auth: Bearer MCP_SECRET."""
    data = await file.read()
    name = (filename or file.filename or "").strip()
    result = WorkspaceAgentClass().upload_file(name, data, agent_id or None)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))
