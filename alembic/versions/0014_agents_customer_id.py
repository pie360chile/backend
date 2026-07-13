"""Add customer_id to agents (one agent catalog per client).

Revision ID: 0014_agents_customer_id
Revises: 0013_agents_customer_budgets
"""

from alembic import op
import sqlalchemy as sa

revision = "0014_agents_customer_id"
down_revision = "0013_agents_customer_budgets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("customer_id", sa.Integer(), nullable=True))
    op.create_index("ix_agents_customer_id", "agents", ["customer_id"])
    op.create_index(
        "ix_agents_customer_id_name",
        "agents",
        ["customer_id", "name"],
    )


def downgrade() -> None:
    op.drop_index("ix_agents_customer_id_name", table_name="agents")
    op.drop_index("ix_agents_customer_id", table_name="agents")
    op.drop_column("agents", "customer_id")
