"""Tabla agent_v2_agents para agentes configurables con prompt."""

from alembic import op
import sqlalchemy as sa

revision = "0009_agent_v2"
down_revision = "0008_schools_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_v2_agents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role_instructions", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("agent_v2_agents")
