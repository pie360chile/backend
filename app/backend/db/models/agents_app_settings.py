"""Ajustes globales de Agentes (Workspace token + Google Drive)."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.backend.db.database import Base


class AgentsAppSettingModel(Base):
    __tablename__ = "agents_app_settings"

    id = Column(Integer, primary_key=True, autoincrement=False)
    default_agent_id = Column(String(64), nullable=True)
    llm_api_key = Column(Text, nullable=True)
    google_drive_root_folder_id = Column(String(255), nullable=True)
    google_service_account_json = Column(Text, nullable=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
