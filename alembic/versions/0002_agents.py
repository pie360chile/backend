"""Revision: tablas agents y agent_files."""

from alembic import op
import sqlalchemy as sa

revision = "0002_agents"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role_instructions", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "agent_files",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_files_agent_id", "agent_files", ["agent_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_files_agent_id", table_name="agent_files")
    op.drop_table("agent_files")
    op.drop_table("agents")
