from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.backend.db.database import Base


class AgentModel(Base):
    __tablename__ = "agents"

    id = Column(String(64), primary_key=True)
    customer_id = Column(Integer, nullable=True, index=True)
    name = Column(String(255), nullable=False)
    role_instructions = Column(Text, nullable=False)
    workspace_trigger_url = Column(Text, nullable=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
