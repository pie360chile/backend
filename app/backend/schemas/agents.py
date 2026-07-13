from pydantic import BaseModel, Field


class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Nombre del agente")
    role_instructions: str = Field(
        ...,
        min_length=1,
        description="Prompt con instrucciones de comportamiento del agente",
    )
    customer_id: int | None = Field(
        default=None,
        description="Cliente dueño del agente (solo superadmin puede elegir otro).",
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


class AgentsSettingsUpdateRequest(BaseModel):
    selected_model_code: str | None = Field(
        default=None,
        description="Código del modelo LLM global (ej. deepseek-chat).",
    )
    selected_model_name: str | None = Field(
        default=None,
        description="Nombre visible del modelo (ej. DeepSeek-V3.2).",
    )
    default_agent_id: str | None = Field(
        default=None,
        description="Agente por defecto para la web (UUID).",
    )
    clear_default_agent: bool = Field(
        default=False,
        description="Si true, limpia el agente por defecto.",
    )
