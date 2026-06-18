"""Revision: chunks indexados por agente para búsqueda."""

from alembic import op
import sqlalchemy as sa

revision = "0003_agent_file_chunks"
down_revision = "0002_agents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_file_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("file_id", sa.String(length=255), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["agent_files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_file_chunks_agent_id", "agent_file_chunks", ["agent_id"])
    op.create_index("ix_agent_file_chunks_file_id", "agent_file_chunks", ["file_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_file_chunks_file_id", table_name="agent_file_chunks")
    op.drop_index("ix_agent_file_chunks_agent_id", table_name="agent_file_chunks")
    op.drop_table("agent_file_chunks")
