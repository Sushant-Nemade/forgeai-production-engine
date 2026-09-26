"""Initial factory run schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "factory_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("brief", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_factory_runs_state", "factory_runs", ["state"])


def downgrade() -> None:
    op.drop_index("ix_factory_runs_state", table_name="factory_runs")
    op.drop_table("factory_runs")
