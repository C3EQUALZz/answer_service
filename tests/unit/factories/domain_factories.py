"""Builders for the domain values the command handlers work with.

Every builder takes only the fields a test actually cares about and fills the
rest with valid defaults, so a test reads as the one thing it is varying.
"""

from datetime import UTC, datetime
from uuid import UUID

from answer_service.application.common.ports.source_file.source_row import SourceRow
from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.entities.qa_pair import QAPair
from answer_service.domain.indexing.value_objects.answer import Answer
from answer_service.domain.indexing.value_objects.category import Category
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.qa_content import QAContent
from answer_service.domain.indexing.value_objects.question import Question
from answer_service.domain.indexing.value_objects.source_reference import SourceReference
from answer_service.domain.indexing.value_objects.task_id import TaskId

SOURCE_UPDATED_AT = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def make_task_id(value: str = "11111111-1111-1111-1111-111111111111") -> TaskId:
    return TaskId(UUID(value))


def make_source_reference(value: str = "uploads/faq.csv") -> SourceReference:
    return SourceReference(value=value)


def make_source_row(
    external_id: str,
    question: str = "How do I reset my password?",
    answer: str = "Use the reset link on the login page.",
    category: str = "account",
    updated_at: datetime = SOURCE_UPDATED_AT,
) -> SourceRow:
    return SourceRow(
        external_id=external_id,
        question=question,
        answer=answer,
        category=category,
        updated_at=updated_at,
    )


def make_qa_content(
    question: str = "How do I reset my password?",
    answer: str = "Use the reset link on the login page.",
    category: str = "account",
) -> QAContent:
    return QAContent(
        question=Question(content=question),
        answer=Answer(content=answer),
        category=Category(value=category),
    )


def make_qa_pair(
    external_id: str,
    events_collection: EventsCollection,
    content: QAContent | None = None,
) -> QAPair:
    return QAPair.register(
        external_id=ExternalId(value=external_id),
        content=content if content is not None else make_qa_content(),
        source_updated_at=SOURCE_UPDATED_AT,
        events_collection=events_collection,
    )
