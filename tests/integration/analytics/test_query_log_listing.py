"""The request-journal listing against a real database.

The unit tests pin the handler's decisions against an in-memory stub that
re-implements the filtering in Python — which means the stub can agree with SQL
that is wrong. These tests settle what only Postgres can: that the ``WHERE``,
the ``ORDER BY`` and the ``LIMIT/OFFSET`` do what the stub assumes, and that the
value objects survive the round trip through the composite columns.
"""

from datetime import UTC, datetime, timedelta

import pytest
from dishka import FromDishka

from answer_service.application.common.ports.gateways import (
    AnalyticsQueryGateway,
    QueryLogFilters,
)
from answer_service.application.common.query_params.pagination import Pagination
from answer_service.application.common.query_params.sorting import SortingOrder
from answer_service.domain.analytics.value_objects.error_code import ErrorCode
from answer_service.domain.analytics.value_objects.period import Period
from answer_service.domain.analytics.value_objects.query_execution import QueryExecution
from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from answer_service.domain.analytics.value_objects.query_status import QueryStatus
from tests.integration.arrange import QueryLogStorer
from tests.integration.inject import inject

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.usefixtures("clean_tables"),
]

NOW = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
WINDOW = Period(start=NOW - timedelta(days=1), end=NOW + timedelta(days=1))
ALL_RESULTS = Pagination(limit=100)
NEWEST_FIRST = SortingOrder.DESC
FAILED = QueryExecution.failed(ErrorCode(value="SearchIndexError"))


@inject
async def test_a_stored_request_is_read_back_field_for_field(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    await store_query_log(
        "how do I export data?",
        results_count=2,
        latency_ms=88,
        occurred_at=NOW,
        category="technical",
    )

    (entry,) = await analytics.read_query_logs(
        QueryLogFilters(period=WINDOW),
        ALL_RESULTS,
        NEWEST_FIRST,
    )

    assert entry.text == "how do I export data?"
    assert entry.results_count == 2
    assert entry.latency_ms == 88
    assert entry.category == "technical"
    assert entry.status is QueryStatus.SUCCEEDED
    assert entry.error_code is None


@inject
async def test_a_failed_request_round_trips_its_status_and_code(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    """The composite must reconstruct the failure from its two columns."""
    await store_query_log("broke", results_count=0, occurred_at=NOW, execution=FAILED)

    (entry,) = await analytics.read_query_logs(
        QueryLogFilters(period=WINDOW),
        ALL_RESULTS,
        NEWEST_FIRST,
    )

    assert entry.status is QueryStatus.FAILED
    assert entry.error_code == "SearchIndexError"


@inject
async def test_the_kind_filter_is_applied_by_the_database(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    await store_query_log("searched", occurred_at=NOW, kind=QueryKind.SEARCH)
    await store_query_log("asked", occurred_at=NOW, kind=QueryKind.ASK)

    entries = await analytics.read_query_logs(
        QueryLogFilters(period=WINDOW, kind=QueryKind.ASK),
        ALL_RESULTS,
        NEWEST_FIRST,
    )

    assert [entry.text for entry in entries] == ["asked"]


@inject
async def test_the_status_filter_is_applied_by_the_database(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    await store_query_log("ok", occurred_at=NOW)
    await store_query_log("broke", results_count=0, occurred_at=NOW, execution=FAILED)

    entries = await analytics.read_query_logs(
        QueryLogFilters(period=WINDOW, status=QueryStatus.FAILED),
        ALL_RESULTS,
        NEWEST_FIRST,
    )

    assert [entry.text for entry in entries] == ["broke"]


@inject
async def test_entries_are_ordered_by_arrival_newest_first(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    await store_query_log("older", occurred_at=NOW - timedelta(hours=2))
    await store_query_log("newer", occurred_at=NOW)

    entries = await analytics.read_query_logs(
        QueryLogFilters(period=WINDOW),
        ALL_RESULTS,
        NEWEST_FIRST,
    )

    assert [entry.text for entry in entries] == ["newer", "older"]


@inject
async def test_ascending_order_reverses_the_page(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    await store_query_log("older", occurred_at=NOW - timedelta(hours=2))
    await store_query_log("newer", occurred_at=NOW)

    entries = await analytics.read_query_logs(
        QueryLogFilters(period=WINDOW),
        ALL_RESULTS,
        SortingOrder.ASC,
    )

    assert [entry.text for entry in entries] == ["older", "newer"]


@inject
async def test_pages_partition_the_journal(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    for index in range(6):
        await store_query_log(f"q-{index}", occurred_at=NOW - timedelta(minutes=index))

    first = await analytics.read_query_logs(
        QueryLogFilters(period=WINDOW),
        Pagination(limit=3, offset=0),
        NEWEST_FIRST,
    )
    second = await analytics.read_query_logs(
        QueryLogFilters(period=WINDOW),
        Pagination(limit=3, offset=3),
        NEWEST_FIRST,
    )

    first_texts = [entry.text for entry in first]
    second_texts = [entry.text for entry in second]
    assert len(first_texts) == len(second_texts) == 3
    assert set(first_texts).isdisjoint(second_texts)


@inject
async def test_the_count_ignores_paging_but_honours_filters(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    await store_query_log("ok-1", occurred_at=NOW)
    await store_query_log("ok-2", occurred_at=NOW)
    await store_query_log("broke", results_count=0, occurred_at=NOW, execution=FAILED)

    total = await analytics.count_query_logs(QueryLogFilters(period=WINDOW))
    failures = await analytics.count_query_logs(
        QueryLogFilters(period=WINDOW, status=QueryStatus.FAILED),
    )

    assert total == 3
    assert failures == 1


@inject
async def test_the_listing_respects_the_period(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    await store_query_log("recent", occurred_at=NOW)
    await store_query_log("ancient", occurred_at=NOW - timedelta(days=90))

    entries = await analytics.read_query_logs(
        QueryLogFilters(period=WINDOW),
        ALL_RESULTS,
        NEWEST_FIRST,
    )

    assert [entry.text for entry in entries] == ["recent"]
