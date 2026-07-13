"""Ajustes globales de Agentes (modelo / agente por defecto para la web)."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.backend.db.database import Base


class AgentsAppSettingModel(Base):
    __tablename__ = "agents_app_settings"

    id = Column(Integer, primary_key=True, autoincrement=False)
    default_agent_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
