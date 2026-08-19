"""Create evaluation_area_templates table.

Revision ID: 0016_evaluation_area_templates
Revises: 0015_document_format_models
"""

from alembic import op
import sqlalchemy as sa

revision = "0016_evaluation_area_templates"
down_revision = "0015_document_format_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluation_area_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("area_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "customer_id",
            "area_id",
            "name",
            name="uq_evaluation_area_templates_customer_area_name",
        ),
    )
    op.create_index(
        "ix_evaluation_area_templates_customer_id",
        "evaluation_area_templates",
        ["customer_id"],
    )
    op.create_index(
        "ix_evaluation_area_templates_area_id",
        "evaluation_area_templates",
        ["area_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_evaluation_area_templates_area_id",
        table_name="evaluation_area_templates",
    )
    op.drop_index(
        "ix_evaluation_area_templates_customer_id",
        table_name="evaluation_area_templates",
    )
    op.drop_table("evaluation_area_templates")
