"""Cola persistente para sincronizar documentos nuevos de estudiantes con Drive."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.backend.db.database import Base


class StudentDriveSyncJobModel(Base):
    __tablename__ = "student_drive_sync_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    folder_id = Column(Integer, nullable=False, index=True)
    student_id = Column(Integer, nullable=False, index=True)
    document_id = Column(Integer, nullable=False)
    file_path = Column(String(512), nullable=False)
    mime_type = Column(String(128), nullable=True)
    status = Column(String(24), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime(), nullable=False, default=datetime.utcnow, index=True)
    locked_at = Column(DateTime(), nullable=True)
    last_error = Column(Text, nullable=True)
    drive_file_id = Column(String(255), nullable=True)
    drive_path = Column(String(1024), nullable=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime(),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    completed_at = Column(DateTime(), nullable=True)
