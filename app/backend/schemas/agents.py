from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = None
    name: str = "Nuevo agente"
    role_instructions: str = Field(
        default="",
        validation_alias=AliasChoices("roleInstructions", "role_instructions"),
    )


class AgentUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = None
    role_instructions: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("roleInstructions", "role_instructions"),
    )


class AgentKnowledgeSearch(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    query: str
    top_k: int = Field(default=5, ge=1, le=20, validation_alias=AliasChoices("topK", "top_k"))


class AgentChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    top_k: int = Field(default=5, ge=1, le=20, validation_alias=AliasChoices("topK", "top_k"))
