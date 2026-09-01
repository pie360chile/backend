"""Create persistent student document Drive sync queue.

Revision ID: 0017_student_drive_sync_jobs
Revises: 0016_evaluation_area_templates
"""

from alembic import op
import sqlalchemy as sa


revision = "0017_student_drive_sync_jobs"
down_revision = "0016_evaluation_area_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_drive_sync_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("folder_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("drive_file_id", sa.String(length=255), nullable=True),
        sa.Column("drive_path", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_student_drive_sync_jobs_folder_id",
        "student_drive_sync_jobs",
        ["folder_id"],
    )
    op.create_index(
        "ix_student_drive_sync_jobs_student_id",
        "student_drive_sync_jobs",
        ["student_id"],
    )
    op.create_index(
        "ix_student_drive_sync_jobs_status",
        "student_drive_sync_jobs",
        ["status"],
    )
    op.create_index(
        "ix_student_drive_sync_jobs_next_attempt_at",
        "student_drive_sync_jobs",
        ["next_attempt_at"],
    )
    op.create_index(
        "ix_student_drive_sync_jobs_due",
        "student_drive_sync_jobs",
        ["status", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_student_drive_sync_jobs_due", table_name="student_drive_sync_jobs")
    op.drop_index(
        "ix_student_drive_sync_jobs_next_attempt_at",
        table_name="student_drive_sync_jobs",
    )
    op.drop_index("ix_student_drive_sync_jobs_status", table_name="student_drive_sync_jobs")
    op.drop_index(
        "ix_student_drive_sync_jobs_student_id",
        table_name="student_drive_sync_jobs",
    )
    op.drop_index(
        "ix_student_drive_sync_jobs_folder_id",
        table_name="student_drive_sync_jobs",
    )
    op.drop_table("student_drive_sync_jobs")
