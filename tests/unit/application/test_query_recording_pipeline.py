"""The pipeline that writes every served query into the analytics journal.

Recording used to be a call at each route, which meant an endpoint could serve a
query without counting it and nothing would fail — the reports would just quietly
under-report. These tests hold the pipeline to what that call site never
guaranteed: that the entry is written from the request itself, that a failure to
write cannot fail the request, and that the marker covers a query nobody
remembered to register.
"""

import asyncio
from typing import Any

import pytest

from answer_service.application.common.analytics import RecordableQuery
from answer_service.application.common.mediator.markers import Command, Query
from answer_service.application.pipelines.query_recording_pipeline import (
    QueryRecordingPipeline,
)
from answer_service.application.queries.conversation.ask_question.query import (
    AskQuestionQuery,
)
from answer_service.application.queries.search.search_qa_pairs.query import (
    SearchQAPairsQuery,
)
from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from answer_service.domain.common.error import AppError
from answer_service.domain.search.value_objects.category_filter import CategoryFilter
from answer_service.domain.search.value_objects.search_criteria import SearchCriteria
from answer_service.domain.search.value_objects.search_query import SearchQuery
from answer_service.domain.search.value_objects.top_k import TopK
from answer_service.infrastructure.mediator import Registry
from tests.unit.stubs.gateways import InMemoryAnalytics
from tests.unit.stubs.infrastructure import CallJournal


class StubOutcome:
    """A response shaped like the one the pipeline reads."""

    def __init__(self, results_count: int, top_score: float | None) -> None:
        self._results_count = results_count
        self._top_score = top_score

    @property
    def results_count(self) -> int:
        return self._results_count

    @property
    def top_score(self) -> float | None:
        return self._top_score


def criteria(
    text: str = "how do I export data?",
    category: str | None = None,
) -> SearchCriteria:
    return SearchCriteria(
        query=SearchQuery(content=text),
        top_k=TopK(value=5),
        category=CategoryFilter(value=category) if category is not None else None,
    )


def served(results_count: int = 4, top_score: float | None = 0.87) -> StubOutcome:
    return StubOutcome(results_count, top_score)


async def run(
    pipeline: QueryRecordingPipeline[Any, Any],
    request: RecordableQuery[Any],
    response: StubOutcome,
) -> Any:
    async def handle_next(_: RecordableQuery[Any]) -> StubOutcome:
        await asyncio.sleep(0)
        return response

    return await pipeline.handle(request, handle_next)


async def test_a_served_query_is_written_to_the_journal(
    query_recording_pipeline: QueryRecordingPipeline[Any, Any],
    analytics: InMemoryAnalytics,
) -> None:
    await run(
        query_recording_pipeline,
        SearchQAPairsQuery(criteria=criteria(category="billing")),
        served(results_count=4, top_score=0.87),
    )

    log = analytics.logs[0]
    assert log.text.content == "how do I export data?"
    assert log.kind is QueryKind.SEARCH
    assert log.outcome.results_count == 4
    assert log.category is not None
    assert log.category.value == "billing"
    assert not log.is_unanswered


async def test_a_query_with_no_results_is_recorded_as_unanswered(
    query_recording_pipeline: QueryRecordingPipeline[Any, Any],
    analytics: InMemoryAnalytics,
) -> None:
    """The gap report is built entirely on this flag."""
    await run(
        query_recording_pipeline,
        AskQuestionQuery(criteria=criteria("how do I cancel?")),
        served(results_count=0, top_score=None),
    )

    assert analytics.logs[0].is_unanswered
    assert analytics.logs[0].kind is QueryKind.ASK


async def test_the_entry_is_committed(
    query_recording_pipeline: QueryRecordingPipeline[Any, Any],
    journal: CallJournal,
) -> None:
    """Queries run outside the transaction pipeline, so this is the only writer."""
    await run(
        query_recording_pipeline,
        SearchQAPairsQuery(criteria=criteria()),
        served(),
    )

    assert journal.entries == ["commit"]


async def test_the_measured_latency_is_the_one_recorded(
    query_recording_pipeline: QueryRecordingPipeline[Any, Any],
    analytics: InMemoryAnalytics,
) -> None:
    """Latency comes from around the handler, not from anything the caller passed."""
    await run(
        query_recording_pipeline,
        SearchQAPairsQuery(criteria=criteria()),
        served(),
    )

    assert analytics.logs[0].latency.milliseconds >= 0


async def test_a_failure_to_record_does_not_fail_the_request(
    query_recording_pipeline: QueryRecordingPipeline[Any, Any],
    analytics: InMemoryAnalytics,
    journal: CallJournal,
) -> None:
    """The caller already has their answer; losing a report row is the lesser harm."""
    analytics.fail_on_add = True
    response = served()

    returned = await run(
        query_recording_pipeline,
        SearchQAPairsQuery(criteria=criteria()),
        response,
    )

    assert returned is response
    assert analytics.logs == []
    assert journal.entries == ["rollback"]


async def test_a_handler_error_reaches_the_caller_and_records_nothing(
    query_recording_pipeline: QueryRecordingPipeline[Any, Any],
    analytics: InMemoryAnalytics,
) -> None:
    """A query that never completed is not a served query."""

    async def handle_next(_: RecordableQuery[Any]) -> StubOutcome:
        await asyncio.sleep(0)
        msg = "the retriever is down"
        raise AppError(msg)

    query = SearchQAPairsQuery(criteria=criteria())

    with pytest.raises(AppError):
        await query_recording_pipeline.handle(query, handle_next)

    assert analytics.logs == []


def test_the_marker_covers_every_recordable_query_and_nothing_else() -> None:
    """Registering against the marker is what stops a new query escaping the report.

    A query that forgets to inherit ``RecordableQuery`` is not journalled — that
    is the one way left to serve a request uncounted, and it is a type error a
    reader can see rather than a missing call they cannot.
    """
    registry = Registry()
    registry.add_pipeline_handlers(RecordableQuery, QueryRecordingPipeline)

    assert registry.get_pipeline_handlers(SearchQAPairsQuery) == [QueryRecordingPipeline]
    assert registry.get_pipeline_handlers(AskQuestionQuery) == [QueryRecordingPipeline]
    assert registry.get_pipeline_handlers(Query) == []
    assert registry.get_pipeline_handlers(Command) == []
