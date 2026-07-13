from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, UniqueConstraint

from app.backend.db.database import Base


class AgentsOpenAIModel(Base):
    """Catálogo de modelos OpenAI para agentes (precios editables + modelo activo)."""

    __tablename__ = "agents_openai_models"
    __table_args__ = (
        UniqueConstraint("model_code", name="uq_agents_openai_models_model_code"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_code = Column(String(64), nullable=False)
    display_name = Column(String(128), nullable=False)
    input_per_1m_usd = Column(Numeric(12, 6), nullable=False, default=0)
    output_per_1m_usd = Column(Numeric(12, 6), nullable=False, default=0)
    cached_input_per_1m_usd = Column(Numeric(12, 6), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_selected = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
