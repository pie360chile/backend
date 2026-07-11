"""Modelos SQLAlchemy por dominio — import compatible con el monolito anterior."""

from app.backend.db.models.erp_legacy import *  # noqa: F401,F403
from app.backend.db.models.pie_core import *  # noqa: F401,F403
from app.backend.db.models.pedagogical import *  # noqa: F401,F403
from app.backend.db.models.agent import AgentModel  # noqa: F401
from app.backend.db.models.agents_documents import AgentDocumentTemplateModel  # noqa: F401
from app.backend.db.models.agents_usage import AgentsTokenUsageModel  # noqa: F401
