"""Create document_format_models table.

Revision ID: 0015_document_format_models
Revises: 0014_agents_customer_id
"""

from alembic import op
import sqlalchemy as sa

revision = "0015_document_format_models"
down_revision = "0014_agents_customer_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_format_models",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", name="uq_document_format_models_document_id"),
    )
    op.create_index(
        "ix_document_format_models_document_id",
        "document_format_models",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_format_models_document_id",
        table_name="document_format_models",
    )
    op.drop_table("document_format_models")
