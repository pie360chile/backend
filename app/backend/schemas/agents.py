from pydantic import BaseModel, Field


class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Nombre del agente")
    role_instructions: str = Field(
        ...,
        min_length=1,
        description="Prompt con instrucciones de comportamiento del agente",
    )


class AgentCreateFolderRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_path: str = Field(default="")


class AgentItem(BaseModel):
    id: str
    name: str
    roleInstructions: str
    updatedAt: str | None = None
    fileCount: int | None = None


class AgentChatHistoryMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    student_id: int | None = None
    student_rut: str | None = Field(default=None, description="RUT/IPE para ubicar al estudiante")
    document_id: int | None = None
    history: list[AgentChatHistoryMessage] = Field(default_factory=list)
