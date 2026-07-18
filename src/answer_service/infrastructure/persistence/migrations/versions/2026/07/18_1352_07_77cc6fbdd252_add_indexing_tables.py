"""add indexing tables

Revision ID: 77cc6fbdd252
Revises:
Create Date: 2026-07-18 13:52:07.175706

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "77cc6fbdd252"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "qa_pairs",
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("external_id", name=op.f("pk_qa_pairs")),
    )
    op.create_index(
        op.f("ix_qa_pairs_category"),
        "qa_pairs",
        ["category"],
        unique=False,
    )

    op.create_table(
        "indexing_tasks",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("failure", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_indexing_tasks")),
    )
    op.create_index(
        op.f("ix_indexing_tasks_status"),
        "indexing_tasks",
        ["status"],
        unique=False,
    )

    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_messages")),
    )
    op.create_index(
        op.f("ix_outbox_messages_event_type"),
        "outbox_messages",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_outbox_messages_created_at"),
        "outbox_messages",
        ["created_at"],
        unique=False,
    )
    # The relay reads only unprocessed rows; a partial index keeps that scan
    # proportional to the backlog instead of to the whole history.
    op.create_index(
        "ix_outbox_messages_pending",
        "outbox_messages",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("processed_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_outbox_messages_pending", table_name="outbox_messages")
    op.drop_index(op.f("ix_outbox_messages_created_at"), table_name="outbox_messages")
    op.drop_index(op.f("ix_outbox_messages_event_type"), table_name="outbox_messages")
    op.drop_table("outbox_messages")

    op.drop_index(op.f("ix_indexing_tasks_status"), table_name="indexing_tasks")
    op.drop_table("indexing_tasks")

    op.drop_index(op.f("ix_qa_pairs_category"), table_name="qa_pairs")
    op.drop_table("qa_pairs")
