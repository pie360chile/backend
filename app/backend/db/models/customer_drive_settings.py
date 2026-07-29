"""Google Drive OAuth/credenciales por customer (cada cliente su nube)."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.backend.db.database import Base


class CustomerDriveSettingModel(Base):
    __tablename__ = "customer_drive_settings"

    customer_id = Column(Integer, primary_key=True, autoincrement=False)
    root_folder_id = Column(String(255), nullable=True)
    # JSON OAuth (client_id, client_secret, refresh_token) o service_account
    credentials_json = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
