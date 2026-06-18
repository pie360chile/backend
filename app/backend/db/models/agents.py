from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text

from app.backend.db.database import Base


class AgentModel(Base):
    __tablename__ = "agents"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False, default="Nuevo agente")
    role_instructions = Column(Text, nullable=False, default="")
    openai_container_id = Column(String(128), nullable=True)
    openai_container_updated_at = Column(DateTime(), nullable=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentFileModel(Base):
    __tablename__ = "agent_files"

    id = Column(String(1024), primary_key=True)
    agent_id = Column(
        String(64),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name = Column(String(1024), nullable=False)
    size_bytes = Column(BigInteger, nullable=False, default=0)
    openai_file_id = Column(String(128), nullable=True, index=True)
    openai_upload_error = Column(Text, nullable=True)
    uploaded_at = Column(DateTime(), nullable=False, default=datetime.utcnow)


class AgentResponseFileModel(Base):
    __tablename__ = "agent_response_files"

    id = Column(String(255), primary_key=True)
    agent_id = Column(
        String(64),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name = Column(String(1024), nullable=False)
    size_bytes = Column(BigInteger, nullable=False, default=0)
    openai_container_id = Column(String(128), nullable=True)
    openai_file_id = Column(String(128), nullable=True, index=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)


class AgentFileChunkModel(Base):
    __tablename__ = "agent_file_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(
        String(64),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id = Column(
        String(1024),
        ForeignKey("agent_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False, default=0)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
