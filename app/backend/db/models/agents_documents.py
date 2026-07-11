from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint

from app.backend.db.database import Base


class AgentDocumentTemplateModel(Base):
    __tablename__ = "agents_document_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(64), nullable=False, index=True)
    document_id = Column(Integer, nullable=False)
    document_name = Column(String(255), nullable=False)
    format_type = Column(String(8), nullable=False)
    template_path = Column(String(512), nullable=False)
    detected_fields = Column(Text, nullable=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("agent_id", "document_id", name="uq_agents_document_template"),
    )
