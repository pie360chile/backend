"""Archivos generados por el code interpreter (PDF, Excel, Word, etc.)."""

from alembic import op
import sqlalchemy as sa

revision = "0006_agent_response_files"
down_revision = "0005_openai_agent_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_response_files",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=1024), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("openai_container_id", sa.String(length=128), nullable=True),
        sa.Column("openai_file_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_response_files_agent_id", "agent_response_files", ["agent_id"])
    op.create_index("ix_agent_response_files_openai_file_id", "agent_response_files", ["openai_file_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_response_files_openai_file_id", table_name="agent_response_files")
    op.drop_index("ix_agent_response_files_agent_id", table_name="agent_response_files")
    op.drop_table("agent_response_files")
