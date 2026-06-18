"""OpenAI file IDs y contenedor de code interpreter por agente."""

from alembic import op
import sqlalchemy as sa

revision = "0005_openai_agent_integration"
down_revision = "0004_agent_file_paths"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("openai_container_id", sa.String(length=128), nullable=True))
    op.add_column("agents", sa.Column("openai_container_updated_at", sa.DateTime(), nullable=True))
    op.add_column("agent_files", sa.Column("openai_file_id", sa.String(length=128), nullable=True))
    op.add_column("agent_files", sa.Column("openai_upload_error", sa.Text(), nullable=True))
    op.create_index("ix_agent_files_openai_file_id", "agent_files", ["openai_file_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_files_openai_file_id", table_name="agent_files")
    op.drop_column("agent_files", "openai_upload_error")
    op.drop_column("agent_files", "openai_file_id")
    op.drop_column("agents", "openai_container_updated_at")
    op.drop_column("agents", "openai_container_id")
