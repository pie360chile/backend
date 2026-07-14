from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text

from app.backend.db.database import Base


class AgentsMcpSaveModel(Base):
    __tablename__ = "agents_mcp_saves"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(64), nullable=False, index=True)
    customer_id = Column(Integer, nullable=False, index=True)
    student_id = Column(Integer, nullable=False)
    document_id = Column(Integer, nullable=False)
    payload_json = Column(Text, nullable=False)
    origin = Column(String(32), nullable=False, default="agent")
    status = Column(String(32), nullable=False, default="pending")
    folder_id = Column(Integer, nullable=True)
    download_url = Column(String(512), nullable=True)
    file_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index(
            "ix_agents_mcp_saves_agent_student_status",
            "agent_id",
            "student_id",
            "status",
        ),
        Index("ix_agents_mcp_saves_created_at", "created_at"),
    )
