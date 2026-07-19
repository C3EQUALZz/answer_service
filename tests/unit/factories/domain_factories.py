"""Builders for the domain values the command handlers work with.

Every builder takes only the fields a test actually cares about and fills the
rest with valid defaults, so a test reads as the one thing it is varying.
"""

from collections import deque
from datetime import UTC, datetime
from uuid import UUID, uuid4

from answer_service.application.common.ports.gateways import IndexingTaskView
from answer_service.application.common.ports.source_file.source_row import SourceRow
from answer_service.domain.analytics.entities.query_log import QueryLog
from answer_service.domain.analytics.value_objects.category_label import CategoryLabel
from answer_service.domain.analytics.value_objects.latency import Latency
from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from answer_service.domain.analytics.value_objects.query_log_id import QueryLogId
from answer_service.domain.analytics.value_objects.query_outcome import QueryOutcome
from answer_service.domain.analytics.value_objects.query_text import QueryText
from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.entities.indexing_task import IndexingTask
from answer_service.domain.indexing.entities.qa_pair import QAPair
from answer_service.domain.indexing.value_objects.answer import Answer
from answer_service.domain.indexing.value_objects.category import Category
from answer_service.domain.indexing.value_objects.content_hash import ContentHash
from answer_service.domain.indexing.value_objects.desired_pair import DesiredPair
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.qa_content import QAContent
from answer_service.domain.indexing.value_objects.question import Question
from answer_service.domain.indexing.value_objects.source_reference import SourceReference
from answer_service.domain.indexing.value_objects.task_id import TaskId
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus
from answer_service.domain.search.value_objects.score import Score
from answer_service.domain.search.value_objects.scored_candidate import ScoredCandidate

SOURCE_UPDATED_AT = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def make_task_id(value: str = "11111111-1111-1111-1111-111111111111") -> TaskId:
    return TaskId(UUID(value))


SOURCE_PATH: str = "uploads/faq.csv"


def make_source_reference(value: str = SOURCE_PATH) -> SourceReference:
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


def make_query_log(
    text: str = "how do I reset my password?",
    *,
    results_count: int = 3,
    occurred_at: datetime = SOURCE_UPDATED_AT,
    latency_ms: int = 42,
    kind: QueryKind = QueryKind.SEARCH,
    category: str | None = None,
) -> QueryLog:
    return QueryLog(
        id=QueryLogId(uuid4()),
        text=QueryText(content=text),
        kind=kind,
        outcome=QueryOutcome(
            results_count=results_count,
            top_score=0.9 if results_count else None,
        ),
        latency=Latency(milliseconds=latency_ms),
        category=CategoryLabel(value=category) if category is not None else None,
        occurred_at=occurred_at,
    )


def make_indexing_task_view(
    task_id: TaskId | None = None,
    status: IndexingTaskStatus = IndexingTaskStatus.SUCCEEDED,
) -> IndexingTaskView:
    return IndexingTaskView(
        task_id=task_id if task_id is not None else make_task_id(),
        status=status,
        source=SOURCE_PATH,
        created_at=SOURCE_UPDATED_AT,
        started_at=SOURCE_UPDATED_AT,
        finished_at=SOURCE_UPDATED_AT,
        created=2,
        updated=1,
        deleted=0,
        skipped=5,
        failure_code=None,
        failure_message=None,
    )


def make_events_collection() -> EventsCollection:
    return EventsCollection(events=deque())


def make_registered_qa_pair(
    external_id: str = "q-1",
    content: QAContent | None = None,
) -> tuple[QAPair, EventsCollection]:
    """A freshly registered pair together with the collection it reports to."""
    collection = make_events_collection()
    pair = QAPair.register(
        external_id=ExternalId(value=external_id),
        content=content if content is not None else make_qa_content(),
        source_updated_at=SOURCE_UPDATED_AT,
        events_collection=collection,
    )
    return pair, collection


def make_queued_indexing_task(
    source: str = SOURCE_PATH,
) -> tuple[IndexingTask, EventsCollection]:
    """A queued task together with the collection it reports to."""
    collection = make_events_collection()
    task = IndexingTask.queue(
        task_id=make_task_id(),
        source=SourceReference(value=source),
        events_collection=collection,
    )
    return task, collection


def make_desired_pair(external_id: str, answer: str = "A.") -> DesiredPair:
    return DesiredPair(
        external_id=ExternalId(value=external_id),
        content=make_qa_content(answer=answer),
        source_updated_at=SOURCE_UPDATED_AT,
    )


def make_manifest(*pairs: DesiredPair) -> dict[ExternalId, ContentHash]:
    """The catalog fingerprints the planner diffs against."""
    return {pair.external_id: pair.fingerprint for pair in pairs}


def make_scored_candidates(*specs: tuple[str, float]) -> list[ScoredCandidate]:
    """Candidates as a retriever returns them: already ordered, best first."""
    return [
        ScoredCandidate(external_id=ExternalId(value=eid), score=Score(value=score))
        for eid, score in specs
    ]
