"""Ampliar rutas de archivos de agente para subida de carpetas."""

from alembic import op
import sqlalchemy as sa

revision = "0004_agent_file_paths"
down_revision = "0003_agent_file_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("agent_files", "id", existing_type=sa.String(length=255), type_=sa.String(length=1024))
    op.alter_column(
        "agent_files",
        "display_name",
        existing_type=sa.String(length=255),
        type_=sa.String(length=1024),
    )
    op.alter_column(
        "agent_file_chunks",
        "file_id",
        existing_type=sa.String(length=255),
        type_=sa.String(length=1024),
    )


def downgrade() -> None:
    op.alter_column(
        "agent_file_chunks",
        "file_id",
        existing_type=sa.String(length=1024),
        type_=sa.String(length=255),
    )
    op.alter_column(
        "agent_files",
        "display_name",
        existing_type=sa.String(length=1024),
        type_=sa.String(length=255),
    )
    op.alter_column("agent_files", "id", existing_type=sa.String(length=1024), type_=sa.String(length=255))
