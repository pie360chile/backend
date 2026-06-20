from __future__ import annotations

from fastapi import APIRouter, status

from app.backend.classes.workspace_agent_class import WorkspaceAgentClass
from app.backend.core.responses import api_error, api_response
from app.backend.schemas.workspace_agent import WorkspaceChatRequest

workspace_agent = APIRouter(
    prefix="/workspace-agent",
    tags=["WorkspaceAgent"],
)


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
