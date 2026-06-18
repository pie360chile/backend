"""Baseline — BD ya existente antes de Alembic.

Para marcar el estado actual sin aplicar DDL:
    alembic stamp head
"""

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
