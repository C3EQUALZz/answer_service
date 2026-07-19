"""add query logs

Revision ID: 21114625167c
Revises: 77cc6fbdd252
Create Date: 2026-07-18 18:16:36.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "21114625167c"
down_revision: str | Sequence[str] | None = "77cc6fbdd252"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "query_logs",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("results_count", sa.Integer(), nullable=False),
        sa.Column("top_score", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_query_logs")),
    )
    op.create_index(op.f("ix_query_logs_kind"), "query_logs", ["kind"], unique=False)
    op.create_index(
        op.f("ix_query_logs_category"),
        "query_logs",
        ["category"],
        unique=False,
    )
    op.create_index(
        "ix_query_logs_occurred_at_text",
        "query_logs",
        ["occurred_at", "text"],
        unique=False,
    )
    op.create_index(
        "ix_query_logs_unanswered",
        "query_logs",
        ["occurred_at"],
        unique=False,
        postgresql_where=sa.text("results_count = 0"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_query_logs_unanswered", table_name="query_logs")
    op.drop_index("ix_query_logs_occurred_at_text", table_name="query_logs")
    op.drop_index(op.f("ix_query_logs_category"), table_name="query_logs")
    op.drop_index(op.f("ix_query_logs_kind"), table_name="query_logs")
    op.drop_table("query_logs")
