"""The analytics read model against a real database.

Every number here is produced by SQL — ``COUNT(*) FILTER``, ``AVG``,
``GROUP BY ... ORDER BY``, ``LIMIT/OFFSET``. The in-memory stub used by the unit
tests re-implements that arithmetic in Python, so it can agree with a query that
is wrong. Only Postgres can settle it.
"""

from datetime import UTC, datetime, timedelta

import pytest
from dishka import FromDishka

from answer_service.application.common.ports.gateways import AnalyticsQueryGateway
from answer_service.application.common.query_params.pagination import Pagination
from answer_service.application.common.query_params.sorting import SortingOrder
from answer_service.domain.analytics.value_objects.period import Period
from tests.integration.arrange import QueryLogStorer
from tests.integration.inject import inject

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.usefixtures("clean_tables"),
]

NOW = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
WINDOW = Period(start=NOW - timedelta(days=1), end=NOW + timedelta(days=1))
DESCENDING = SortingOrder.DESC
ALL_RESULTS = Pagination(limit=100)


@inject
async def test_an_idle_period_reports_zeroes(
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    """A service nobody used must still be able to render its report."""
    statistics = await analytics.read_statistics(WINDOW)

    assert statistics.total == 0
    assert statistics.unanswered == 0
    assert statistics.average_latency_ms == pytest.approx(0.0)
    assert statistics.unanswered_rate == pytest.approx(0.0)


@inject
async def test_answered_and_unanswered_are_counted_apart(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    await store_query_log("answered", results_count=3, occurred_at=NOW)
    await store_query_log("also answered", results_count=1, occurred_at=NOW)
    await store_query_log("a gap", results_count=0, occurred_at=NOW)

    statistics = await analytics.read_statistics(WINDOW)

    assert statistics.total == 3
    assert statistics.unanswered == 1
    assert statistics.answered == 2
    assert statistics.unanswered_rate == pytest.approx(1 / 3)


@inject
async def test_the_average_latency_is_computed_by_the_database(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    await store_query_log("a", latency_ms=100, occurred_at=NOW)
    await store_query_log("b", latency_ms=200, occurred_at=NOW)
    await store_query_log("c", latency_ms=300, occurred_at=NOW)

    statistics = await analytics.read_statistics(WINDOW)

    assert statistics.average_latency_ms == pytest.approx(200.0)


@inject
async def test_the_period_bounds_what_is_counted(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    await store_query_log("inside", occurred_at=NOW)
    await store_query_log("before", occurred_at=NOW - timedelta(days=30))
    await store_query_log("after", occurred_at=NOW + timedelta(days=30))

    statistics = await analytics.read_statistics(WINDOW)

    assert statistics.total == 1


@inject
async def test_the_period_is_half_open_at_its_end(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    """Consecutive periods must tile without counting a boundary query twice."""
    await store_query_log("at the start", occurred_at=WINDOW.start)
    await store_query_log("at the end", occurred_at=WINDOW.end)

    statistics = await analytics.read_statistics(WINDOW)

    assert statistics.total == 1


@inject
async def test_repeated_queries_are_grouped_and_ranked(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    for _ in range(3):
        await store_query_log("asked often", occurred_at=NOW)
    await store_query_log("asked once", occurred_at=NOW)

    popular = await analytics.read_popular_queries(WINDOW, ALL_RESULTS, DESCENDING)

    assert [(query.text, query.occurrences) for query in popular] == [
        ("asked often", 3),
        ("asked once", 1),
    ]


@inject
async def test_the_gap_report_ignores_answered_queries(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    """This list is a backlog of FAQ entries to write; answered ones are noise."""
    await store_query_log("a gap", results_count=0, occurred_at=NOW)
    await store_query_log("answered fine", results_count=5, occurred_at=NOW)

    unanswered = await analytics.read_unanswered_queries(WINDOW, ALL_RESULTS, DESCENDING)

    assert [query.text for query in unanswered] == ["a gap"]


@inject
async def test_the_same_query_can_be_answered_once_and_not_another_time(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    """Only the occurrences that found nothing count towards the gap."""
    await store_query_log("sometimes", results_count=0, occurred_at=NOW)
    await store_query_log("sometimes", results_count=0, occurred_at=NOW)
    await store_query_log("sometimes", results_count=4, occurred_at=NOW)

    unanswered = await analytics.read_unanswered_queries(WINDOW, ALL_RESULTS, DESCENDING)
    popular = await analytics.read_popular_queries(WINDOW, ALL_RESULTS, DESCENDING)

    assert [(q.text, q.occurrences) for q in unanswered] == [("sometimes", 2)]
    assert [(q.text, q.occurrences) for q in popular] == [("sometimes", 3)]


@inject
async def test_ascending_order_surfaces_the_rarest_first(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    await store_query_log("rare", results_count=0, occurred_at=NOW)
    for _ in range(2):
        await store_query_log("common", results_count=0, occurred_at=NOW)

    ascending = await analytics.read_unanswered_queries(
        WINDOW,
        ALL_RESULTS,
        SortingOrder.ASC,
    )

    assert [query.text for query in ascending] == ["rare", "common"]


@inject
async def test_the_backlog_pages_without_repeating_or_skipping(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    """Every gap is asked once, so the counts tie and only the tiebreak orders them.

    Without a deterministic secondary sort a row could land on both pages, or on
    neither — the failure mode that makes a backlog impossible to work through.
    """
    for index in range(6):
        await store_query_log(f"gap-{index}", results_count=0, occurred_at=NOW)

    first_page = await analytics.read_unanswered_queries(
        WINDOW,
        Pagination(limit=3),
        DESCENDING,
    )
    second_page = await analytics.read_unanswered_queries(
        WINDOW,
        Pagination(limit=3, offset=3),
        DESCENDING,
    )

    first_texts = [query.text for query in first_page]
    second_texts = [query.text for query in second_page]
    assert len(first_texts) == len(second_texts) == 3
    assert set(first_texts).isdisjoint(second_texts)
    assert set(first_texts) | set(second_texts) == {f"gap-{index}" for index in range(6)}


@inject
async def test_paging_past_the_end_returns_nothing(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    await store_query_log("only one", results_count=0, occurred_at=NOW)

    beyond = await analytics.read_unanswered_queries(
        WINDOW,
        Pagination(limit=10, offset=50),
        DESCENDING,
    )

    assert beyond == []


@inject
async def test_the_gap_report_respects_the_period(
    store_query_log: QueryLogStorer,
    analytics: FromDishka[AnalyticsQueryGateway],
) -> None:
    await store_query_log("recent gap", results_count=0, occurred_at=NOW)
    await store_query_log(
        "ancient gap",
        results_count=0,
        occurred_at=NOW - timedelta(days=90),
    )

    unanswered = await analytics.read_unanswered_queries(WINDOW, ALL_RESULTS, DESCENDING)

    assert [query.text for query in unanswered] == ["recent gap"]
