from typing import Final

from sqlalchemy import Column, Computed, DateTime, Index, Table
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import composite

from answer_service.domain.indexing.entities.qa_pair import QAPair
from answer_service.domain.indexing.value_objects.qa_content import QAContent
from answer_service.infrastructure.persistence.models.base import mapper_registry
from answer_service.infrastructure.persistence.models.types import (
    AnswerType,
    CategoryType,
    ExternalIdType,
    QuestionType,
)

# Must match the literal baked into migration c8a37b2e4d91. Changing it here
# alone would leave the query using one language and the index another, which
# degrades quietly rather than failing.
TEXT_SEARCH_CONFIG: Final[str] = "english"

SEARCH_VECTOR_COLUMN: Final[str] = "search_vector"

_SEARCH_VECTOR_EXPRESSION: Final[str] = (
    f"setweight(to_tsvector('{TEXT_SEARCH_CONFIG}', coalesce(question, '')), 'A') || "
    f"setweight(to_tsvector('{TEXT_SEARCH_CONFIG}', coalesce(answer, '')), 'B')"
)

qa_pairs_table: Final[Table] = Table(
    "qa_pairs",
    mapper_registry.metadata,
    Column("external_id", ExternalIdType, primary_key=True),
    Column("question", QuestionType, nullable=False),
    Column("answer", AnswerType, nullable=False),
    Column("category", CategoryType, nullable=False, index=True),
    Column("source_updated_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column(
        SEARCH_VECTOR_COLUMN,
        TSVECTOR,
        Computed(_SEARCH_VECTOR_EXPRESSION, persisted=True),
        nullable=True,
    ),
)

Index(
    "ix_qa_pairs_search_vector",
    qa_pairs_table.c.search_vector,
    postgresql_using="gin",
)


def map_qa_pairs_table() -> None:
    """Maps the QAPair aggregate.

    ``content`` is a composite rather than a JSONB blob: ``category`` is filtered
    on at search time and question/answer feed the lexical index, so they have to
    be real columns.

    ``search_vector`` is excluded: it belongs to the lexical retriever, which
    queries the table directly. Mapping it would hang a PostgreSQL detail off the
    domain aggregate for nobody's benefit.
    """
    mapper_registry.map_imperatively(
        QAPair,
        qa_pairs_table,
        exclude_properties=[SEARCH_VECTOR_COLUMN],
        properties={
            "id": qa_pairs_table.c.external_id,
            "content": composite(
                QAContent,
                qa_pairs_table.c.question,
                qa_pairs_table.c.answer,
                qa_pairs_table.c.category,
            ),
            "source_updated_at": qa_pairs_table.c.source_updated_at,
            "created_at": qa_pairs_table.c.created_at,
            "updated_at": qa_pairs_table.c.updated_at,
        },
    )
