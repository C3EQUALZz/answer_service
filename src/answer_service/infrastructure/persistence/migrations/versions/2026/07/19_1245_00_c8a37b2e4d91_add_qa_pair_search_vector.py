"""add qa pair search vector

Revision ID: c8a37b2e4d91
Revises: 21114625167c
Create Date: 2026-07-19 12:45:00.000000

The lexical half of hybrid search. The vector is a stored generated column
rather than a trigger-maintained one, so it cannot drift from the row it
describes: PostgreSQL recomputes it in the same statement that writes the text.

The ``english`` configuration is repeated here as a literal on purpose. A
migration must keep meaning what it meant the day it ran, so it cannot read a
constant the application is free to change; the application-side copy lives in
``persistence.models.qa_pair.TEXT_SEARCH_CONFIG`` and the two must agree.
Changing the language is a new migration, not an edit to this one.

Question text is weighted above answer text: a pair whose *question* matches is
almost always the one the user meant, while answer bodies are long and match
incidentally.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8a37b2e4d91"
down_revision: str | Sequence[str] | None = "21114625167c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEARCH_VECTOR_EXPRESSION: str = (
    "setweight(to_tsvector('english', coalesce(question, '')), 'A') || "
    "setweight(to_tsvector('english', coalesce(answer, '')), 'B')"
)


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "qa_pairs",
        sa.Column(
            "search_vector",
            sa.dialects.postgresql.TSVECTOR(),
            sa.Computed(SEARCH_VECTOR_EXPRESSION, persisted=True),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_qa_pairs_search_vector"),
        "qa_pairs",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_qa_pairs_search_vector"), table_name="qa_pairs")
    op.drop_column("qa_pairs", "search_vector")
