"""Elimina tablas del feature agente (agents, agent_files, etc.)."""

from alembic import op

revision = "0007_drop_agent_tables"
down_revision = "0006_agent_response_files"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_agent_response_files_openai_file_id", table_name="agent_response_files")
    op.drop_index("ix_agent_response_files_agent_id", table_name="agent_response_files")
    op.drop_table("agent_response_files")

    op.drop_index("ix_agent_file_chunks_file_id", table_name="agent_file_chunks")
    op.drop_index("ix_agent_file_chunks_agent_id", table_name="agent_file_chunks")
    op.drop_table("agent_file_chunks")

    op.drop_index("ix_agent_files_openai_file_id", table_name="agent_files")
    op.drop_index("ix_agent_files_agent_id", table_name="agent_files")
    op.drop_table("agent_files")

    op.drop_table("agents")


def downgrade() -> None:
    raise NotImplementedError("No se puede restaurar el feature agente eliminado")
