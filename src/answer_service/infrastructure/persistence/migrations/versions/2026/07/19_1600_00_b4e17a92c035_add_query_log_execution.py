"""add query log execution status and error code

Revision ID: b4e17a92c035
Revises: c8a37b2e4d91
Create Date: 2026-07-19 16:00:00.000000

Splits "how much did it find" from "did it work at all". Until now a query that
raised was not recorded, so the journal held successes only and every row was
implicitly a success — which is why existing rows can be backfilled as
``succeeded`` without guessing.

The partial index for the gap report is rebuilt rather than left alone: with
failures now in the table, ``results_count = 0`` alone would count an outage as
a hole in the catalog and put it on the content backlog.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4e17a92c035"
down_revision: str | Sequence[str] | None = "c8a37b2e4d91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SUCCEEDED: str = "succeeded"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "query_logs",
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=SUCCEEDED,
        ),
    )
    op.add_column("query_logs", sa.Column("error_code", sa.Text(), nullable=True))

    # The default exists only to backfill; new rows state their own status.
    op.alter_column("query_logs", "status", server_default=None)

    op.create_index(
        "ix_query_logs_occurred_at_status_kind",
        "query_logs",
        ["occurred_at", "status", "kind"],
        unique=False,
    )

    op.drop_index("ix_query_logs_unanswered", table_name="query_logs")
    op.create_index(
        "ix_query_logs_unanswered",
        "query_logs",
        ["occurred_at"],
        unique=False,
        # SUCCEEDED is a module-level constant, no user input reaches this text().
        # nosemgrep
        postgresql_where=sa.text(f"results_count = 0 AND status = '{SUCCEEDED}'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_query_logs_unanswered", table_name="query_logs")
    op.create_index(
        "ix_query_logs_unanswered",
        "query_logs",
        ["occurred_at"],
        unique=False,
        postgresql_where=sa.text("results_count = 0"),
    )

    op.drop_index("ix_query_logs_occurred_at_status_kind", table_name="query_logs")
    op.drop_column("query_logs", "error_code")
    op.drop_column("query_logs", "status")
