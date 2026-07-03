from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from app.backend.db.database import Base


class AgentV2Model(Base):
    __tablename__ = "agent_v2_agents"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    role_instructions = Column(Text, nullable=False)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
