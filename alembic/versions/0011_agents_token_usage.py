"""Revision: consumo de tokens de agentes por cliente."""

from alembic import op
import sqlalchemy as sa

revision = "0011_agents_token_usage"
down_revision = "0010_agent_v2_document_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents_token_usage",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("request_kind", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agents_token_usage_customer_id", "agents_token_usage", ["customer_id"])
    op.create_index("ix_agents_token_usage_school_id", "agents_token_usage", ["school_id"])
    op.create_index(
        "ix_agents_token_usage_customer_created",
        "agents_token_usage",
        ["customer_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_agents_token_usage_customer_created", table_name="agents_token_usage")
    op.drop_index("ix_agents_token_usage_school_id", table_name="agents_token_usage")
    op.drop_index("ix_agents_token_usage_customer_id", table_name="agents_token_usage")
    op.drop_table("agents_token_usage")
