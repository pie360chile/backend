"""Revision: renombrar tablas agent_v2_* a agents / agents_document_templates."""

from alembic import op
import sqlalchemy as sa

revision = "0012_rename_agent_v2_to_agents"
down_revision = "0011_agents_token_usage"
branch_labels = None
depends_on = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _rename_index_if_exists(table: str, old_name: str, new_name: str) -> None:
    bind = op.get_bind()
    indexes = {idx["name"] for idx in sa.inspect(bind).get_indexes(table)}
    if old_name in indexes and new_name not in indexes:
        op.execute(sa.text(f"ALTER TABLE `{table}` RENAME INDEX `{old_name}` TO `{new_name}`"))


def _rename_unique_if_exists(table: str, old_name: str, new_name: str) -> None:
    bind = op.get_bind()
    uniques = {uc["name"] for uc in sa.inspect(bind).get_unique_constraints(table)}
    if old_name in uniques and new_name not in uniques:
        # MySQL: drop + recreate unique constraint under the new name
        op.drop_constraint(old_name, table_name=table, type_="unique")
        op.create_unique_constraint(new_name, table, ["agent_id", "document_id"])


def upgrade() -> None:
    bind = op.get_bind()
    tables = _tables(bind)

    if "agent_v2_agents" in tables:
        # 0002 created a legacy `agents` table; drop it so the rename can proceed.
        if "agents" in tables:
            if "agent_files" in tables:
                try:
                    op.drop_index("ix_agent_files_agent_id", table_name="agent_files")
                except Exception:
                    pass
                op.drop_table("agent_files")
            op.drop_table("agents")
        op.rename_table("agent_v2_agents", "agents")

    tables = _tables(bind)
    if "agent_v2_document_templates" in tables:
        op.rename_table("agent_v2_document_templates", "agents_document_templates")
        _rename_index_if_exists(
            "agents_document_templates",
            "ix_agent_v2_document_templates_agent_id",
            "ix_agents_document_templates_agent_id",
        )
        _rename_unique_if_exists(
            "agents_document_templates",
            "uq_agent_v2_document_template",
            "uq_agents_document_template",
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = _tables(bind)

    if "agents_document_templates" in tables:
        _rename_unique_if_exists(
            "agents_document_templates",
            "uq_agents_document_template",
            "uq_agent_v2_document_template",
        )
        _rename_index_if_exists(
            "agents_document_templates",
            "ix_agents_document_templates_agent_id",
            "ix_agent_v2_document_templates_agent_id",
        )
        op.rename_table("agents_document_templates", "agent_v2_document_templates")

    tables = _tables(bind)
    if "agents" in tables and "agent_v2_agents" not in tables:
        op.rename_table("agents", "agent_v2_agents")
