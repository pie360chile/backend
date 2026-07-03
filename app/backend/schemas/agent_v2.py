from pydantic import BaseModel, Field


class AgentV2CreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Nombre del agente")
    role_instructions: str = Field(
        ...,
        min_length=1,
        description="Prompt con instrucciones de comportamiento del agente",
    )


class AgentV2CreateFolderRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_path: str = Field(default="")


class AgentV2Item(BaseModel):
    id: str
    name: str
    roleInstructions: str
    updatedAt: str | None = None
    fileCount: int | None = None


class AgentV2ChatHistoryMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)


class AgentV2ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    student_id: int | None = None
    document_id: int | None = None
    history: list[AgentV2ChatHistoryMessage] = Field(default_factory=list)
