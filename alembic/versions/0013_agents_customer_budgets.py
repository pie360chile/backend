"""agents customer monthly budgets

Revision ID: 0013_agents_customer_budgets
Revises: 0012_rename_agent_v2_to_agents
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa

revision = "0013_agents_customer_budgets"
down_revision = "0012_rename_agent_v2_to_agents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents_customer_budgets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("monthly_budget_usd", sa.Numeric(12, 4), nullable=False),
        sa.Column("buffer_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", name="uq_agents_customer_budgets_customer_id"),
    )
    op.create_index(
        "ix_agents_customer_budgets_customer_id",
        "agents_customer_budgets",
        ["customer_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agents_customer_budgets_customer_id",
        table_name="agents_customer_budgets",
    )
    op.drop_table("agents_customer_budgets")
