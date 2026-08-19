from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from app.backend.db.database import Base


class EvaluationAreaTemplateModel(Base):
    """Plantilla personalizada por área de evaluación (no es documento del estudiante)."""

    __tablename__ = "evaluation_area_templates"
    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            "area_id",
            "name",
            name="uq_evaluation_area_templates_customer_area_name",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, nullable=False, index=True)
    area_id = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_path = Column(String(512), nullable=False)
    content_type = Column(String(128), nullable=True)
    uploaded_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
