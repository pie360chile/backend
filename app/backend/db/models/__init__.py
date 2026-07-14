"""Modelos SQLAlchemy por dominio — import compatible con el monolito anterior."""

from app.backend.db.models.erp_legacy import *  # noqa: F401,F403
from app.backend.db.models.pie_core import *  # noqa: F401,F403
from app.backend.db.models.pedagogical import *  # noqa: F401,F403
from app.backend.db.models.agent import AgentModel  # noqa: F401
from app.backend.db.models.agents_app_settings import AgentsAppSettingModel  # noqa: F401
from app.backend.db.models.agents_documents import AgentDocumentTemplateModel  # noqa: F401
from app.backend.db.models.agents_mcp_saves import AgentsMcpSaveModel  # noqa: F401
from app.backend.db.models.agents_openai_models import AgentsOpenAIModel  # noqa: F401
from app.backend.db.models.agents_usage import (  # noqa: F401
    AgentsBudgetReservationModel,
    AgentsCustomerBudgetModel,
    AgentsRateLimitHitModel,
    AgentsTokenUsageModel,
)
from app.backend.db.models.document_format_models import DocumentFormatModel  # noqa: F401
