from pydantic import BaseModel, Field


class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Nombre del agente")
    role_instructions: str = Field(
        ...,
        min_length=1,
        description="Prompt con instrucciones de comportamiento del agente",
    )
    workspace_trigger_url: str | None = Field(
        default=None,
        description="URL trigger Workspace ChatGPT de este agente (única por agente).",
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
        description="Código del modelo LLM global.",
    )
    selected_model_name: str | None = Field(
        default=None,
        description="Nombre visible del modelo.",
    )
    default_agent_id: str | None = Field(
        default=None,
        description="Agente por defecto para la web (UUID).",
    )
    clear_default_agent: bool = Field(
        default=False,
        description="Si true, limpia el agente por defecto.",
    )
    llm_api_key: str | None = Field(
        default=None,
        description="Token de Workspace ChatGPT. Si no se envía, no se modifica.",
    )
    clear_llm_api_key: bool = Field(
        default=False,
        description="Si true, elimina el token de Workspace guardado.",
    )
    google_drive_root_folder_id: str | None = Field(
        default=None,
        description="ID de la carpeta raíz en Google Drive. Vacío no modifica si no se envía clear.",
    )
    google_service_account_json: str | None = Field(
        default=None,
        description="JSON completo de la cuenta de servicio de Google. Si no se envía, no se modifica.",
    )
    clear_google_drive: bool = Field(
        default=False,
        description="Si true, elimina root folder id y JSON de service account.",
    )
