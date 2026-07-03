"""Modelos SQLAlchemy por dominio — import compatible con el monolito anterior."""

from app.backend.db.models.erp_legacy import *  # noqa: F401,F403
from app.backend.db.models.pie_core import *  # noqa: F401,F403
from app.backend.db.models.pedagogical import *  # noqa: F401,F403
from app.backend.db.models.agent_v2 import AgentV2Model  # noqa: F401
from app.backend.db.models.agent_v2_documents import AgentV2DocumentTemplateModel  # noqa: F401
