"""Revision: plantillas de documento por agente v2."""

from alembic import op
import sqlalchemy as sa

revision = "0010_agent_v2_document_templates"
down_revision = "0009_agent_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_v2_document_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("document_name", sa.String(length=255), nullable=False),
        sa.Column("format_type", sa.String(length=8), nullable=False),
        sa.Column("template_path", sa.String(length=512), nullable=False),
        sa.Column("detected_fields", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "document_id", name="uq_agent_v2_document_template"),
    )
    op.create_index(
        "ix_agent_v2_document_templates_agent_id",
        "agent_v2_document_templates",
        ["agent_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_v2_document_templates_agent_id", table_name="agent_v2_document_templates")
    op.drop_table("agent_v2_document_templates")
