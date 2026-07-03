"""Tabla schools_settings: Google Drive por colegio."""

from alembic import op
import sqlalchemy as sa

revision = "0008_schools_settings"
down_revision = "0007_drop_agent_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schools_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("google_drive_root_folder_id", sa.String(length=255), nullable=True),
        sa.Column("google_service_account_json", sa.Text(), nullable=True),
        sa.Column("added_date", sa.DateTime(), nullable=True),
        sa.Column("updated_date", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", name="uq_schools_settings_school_id"),
    )
    op.create_index("ix_schools_settings_school_id", "schools_settings", ["school_id"])


def downgrade() -> None:
    op.drop_index("ix_schools_settings_school_id", table_name="schools_settings")
    op.drop_table("schools_settings")
