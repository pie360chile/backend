from pydantic import BaseModel, Field


class WorkspaceChatRequest(BaseModel):
    input: str = Field(..., min_length=1, description="Mensaje a enviar al Workspace Agent")


class WorkspaceAgentItem(BaseModel):
    id: str
    name: str
    updatedAt: str | None = None
