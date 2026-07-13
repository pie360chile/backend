from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from app.backend.db.database import Base


class DocumentFormatModel(Base):
    """Plantilla/modelo descargable para documentos de solo carga (sin formulario)."""

    __tablename__ = "document_format_models"
    __table_args__ = (
        UniqueConstraint("document_id", name="uq_document_format_models_document_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_path = Column(String(512), nullable=False)
    content_type = Column(String(128), nullable=True)
    uploaded_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
