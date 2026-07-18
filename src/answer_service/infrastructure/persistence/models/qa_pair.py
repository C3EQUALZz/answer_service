from typing import Final

from sqlalchemy import Column, DateTime, Table
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
)


def map_qa_pairs_table() -> None:
    """Maps the QAPair aggregate.

    ``content`` is a composite rather than a JSONB blob: ``category`` is filtered
    on at search time and question/answer feed the lexical index, so they have to
    be real columns.
    """
    mapper_registry.map_imperatively(
        QAPair,
        qa_pairs_table,
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
