from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Numeric, String

from app.backend.db.database import Base


class AgentsTokenUsageModel(Base):
    """Consumo de tokens OpenAI por cliente (customer_id)."""

    __tablename__ = "agents_token_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, nullable=False, index=True)
    school_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=True)
    agent_id = Column(String(64), nullable=True)
    request_kind = Column(String(32), nullable=False, default="chat")
    model = Column(String(64), nullable=False)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    estimated_cost_usd = Column(Numeric(12, 6), nullable=False, default=0)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
