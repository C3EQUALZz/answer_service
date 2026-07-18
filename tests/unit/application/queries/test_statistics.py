from datetime import UTC, datetime, timedelta

import pytest

from answer_service.application.commands.analytics.record_query.command import (
    RecordQueryCommand,
)
from answer_service.application.commands.analytics.record_query.handler import (
    RecordQueryHandler,
)
from answer_service.application.common.query_params.pagination import Pagination
from answer_service.application.common.query_params.sorting import SortingOrder
from answer_service.application.error import PaginationError
from answer_service.application.queries.analytics.get_statistics.handler import (
    GetStatisticsHandler,
)
from answer_service.application.queries.analytics.get_statistics.query import (
    GetStatisticsQuery,
)
from answer_service.application.queries.analytics.list_unanswered_queries.handler import (
    MAX_LIMIT,
    ListUnansweredQueriesHandler,
)
from answer_service.application.queries.analytics.list_unanswered_queries.query import (
    ListUnansweredQueriesQuery,
)
from answer_service.domain.analytics.value_objects.period import Period
from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from answer_service.domain.common.events_collection import EventsCollection
from tests.unit.factories.domain_factories import (
    SOURCE_UPDATED_AT,
    make_qa_content,
    make_qa_pair,
    make_query_log,
)
from tests.unit.stubs.gateways import InMemoryAnalytics, InMemoryQACatalog

WINDOW = Period(
    start=SOURCE_UPDATED_AT - timedelta(days=1),
    end=SOURCE_UPDATED_AT + timedelta(days=1),
)


async def test_records_a_served_query(
    record_query_handler: RecordQueryHandler,
    analytics: InMemoryAnalytics,
) -> None:
    await record_query_handler.handle(
        RecordQueryCommand(
            text="how do I export data?",
            kind=QueryKind.SEARCH,
            results_count=4,
            latency_ms=120,
            top_score=0.87,
            category="billing",
        ),
    )

    log = analytics.logs[0]
    assert log.text.content == "how do I export data?"
    assert log.kind is QueryKind.SEARCH
    assert log.outcome.results_count == 4
    assert log.latency.milliseconds == 120
    assert log.category is not None
    assert log.category.value == "billing"
    assert not log.is_unanswered


async def test_a_query_with_no_results_is_recorded_as_unanswered(
    record_query_handler: RecordQueryHandler,
    analytics: InMemoryAnalytics,
) -> None:
    """The gap report is built entirely on this flag."""
    await record_query_handler.handle(
        RecordQueryCommand(
            text="how do I cancel?",
            kind=QueryKind.ASK,
            results_count=0,
            latency_ms=90,
        ),
    )

    assert analytics.logs[0].is_unanswered


async def test_statistics_combine_the_catalog_and_the_query_log(
    get_statistics_handler: GetStatisticsHandler,
    catalog: InMemoryQACatalog,
    analytics: InMemoryAnalytics,
    events_collection: EventsCollection,
) -> None:
    await catalog.add(
        make_qa_pair("q-1", events_collection, make_qa_content(category="billing")),
    )
    await catalog.add(
        make_qa_pair("q-2", events_collection, make_qa_content(category="billing")),
    )
    await catalog.add(
        make_qa_pair("q-3", events_collection, make_qa_content(category="account")),
    )
    analytics.logs.extend(
        [
            make_query_log("a", results_count=2, latency_ms=100),
            make_query_log("a", results_count=2, latency_ms=200),
            make_query_log("b", results_count=0, latency_ms=300),
        ],
    )

    response = await get_statistics_handler.handle(GetStatisticsQuery(period=WINDOW))

    assert response.catalog.total_pairs == 3
    assert response.catalog.pairs_per_category == {"billing": 2, "account": 1}
    assert response.catalog.category_count == 2
    assert response.queries.total == 3
    assert response.queries.unanswered == 1
    assert response.queries.answered == 2
    assert response.queries.average_latency_ms == pytest.approx(200.0)
    assert response.popular_queries[0].text == "a"
    assert response.popular_queries[0].occurrences == 2


async def test_statistics_of_an_idle_period_are_zero_not_a_crash(
    get_statistics_handler: GetStatisticsHandler,
) -> None:
    """An unused service must still be able to render its report."""
    response = await get_statistics_handler.handle(GetStatisticsQuery(period=WINDOW))

    assert response.queries.total == 0
    assert response.queries.unanswered_rate == pytest.approx(0.0)
    assert response.popular_queries == ()
    assert response.catalog.total_pairs == 0


async def test_the_period_bounds_what_is_counted(
    get_statistics_handler: GetStatisticsHandler,
    analytics: InMemoryAnalytics,
) -> None:
    analytics.logs.extend(
        [
            make_query_log("inside", occurred_at=SOURCE_UPDATED_AT),
            make_query_log(
                "outside",
                occurred_at=SOURCE_UPDATED_AT - timedelta(days=30),
            ),
        ],
    )

    response = await get_statistics_handler.handle(GetStatisticsQuery(period=WINDOW))

    assert response.queries.total == 1
    assert [q.text for q in response.popular_queries] == ["inside"]


async def test_the_period_is_half_open_at_its_end(
    get_statistics_handler: GetStatisticsHandler,
    analytics: InMemoryAnalytics,
) -> None:
    """Consecutive periods must tile without double-counting a boundary query."""
    analytics.logs.extend(
        [
            make_query_log("at-start", occurred_at=WINDOW.start),
            make_query_log("at-end", occurred_at=WINDOW.end),
        ],
    )

    response = await get_statistics_handler.handle(GetStatisticsQuery(period=WINDOW))

    assert response.queries.total == 1
    assert [q.text for q in response.popular_queries] == ["at-start"]


async def test_unanswered_report_ranks_gaps_by_frequency(
    list_unanswered_handler: ListUnansweredQueriesHandler,
    analytics: InMemoryAnalytics,
) -> None:
    analytics.logs.extend(
        [
            make_query_log("how do I cancel?", results_count=0),
            make_query_log("how do I cancel?", results_count=0),
            make_query_log("how do I cancel?", results_count=0),
            make_query_log("where is my invoice?", results_count=0),
            make_query_log("answered one", results_count=5),
        ],
    )

    response = await list_unanswered_handler.handle(
        ListUnansweredQueriesQuery(period=WINDOW),
    )

    assert [q.text for q in response.queries] == [
        "how do I cancel?",
        "where is my invoice?",
    ]
    assert response.queries[0].occurrences == 3
    assert response.total_occurrences == 4


async def test_unanswered_report_honours_its_limit(
    list_unanswered_handler: ListUnansweredQueriesHandler,
    analytics: InMemoryAnalytics,
) -> None:
    analytics.logs.extend(
        make_query_log(f"gap-{index}", results_count=0) for index in range(5)
    )

    response = await list_unanswered_handler.handle(
        ListUnansweredQueriesQuery(
            period=WINDOW,
            pagination=Pagination(limit=2),
        ),
    )

    assert len(response.queries) == 2


@pytest.mark.parametrize("limit", (0, -1))
def test_a_non_positive_limit_is_rejected_by_pagination(limit: int) -> None:
    """Caught at construction, so a bad page size never reaches a gateway."""
    with pytest.raises(PaginationError):
        Pagination(limit=limit)


def test_a_negative_offset_is_rejected_by_pagination() -> None:
    with pytest.raises(PaginationError):
        Pagination(offset=-1)


async def test_a_limit_above_the_ceiling_is_rejected(
    list_unanswered_handler: ListUnansweredQueriesHandler,
) -> None:
    """The ceiling stops one caller from pulling the whole query log."""
    with pytest.raises(PaginationError, match="200"):
        await list_unanswered_handler.handle(
            ListUnansweredQueriesQuery(
                period=WINDOW,
                pagination=Pagination(limit=MAX_LIMIT + 1),
            ),
        )


async def test_the_backlog_can_be_paged_through(
    list_unanswered_handler: ListUnansweredQueriesHandler,
    analytics: InMemoryAnalytics,
) -> None:
    """The gap report is a backlog: page two must continue, not repeat page one."""
    analytics.logs.extend(
        make_query_log(f"gap-{index}", results_count=0) for index in range(5)
    )

    first = await list_unanswered_handler.handle(
        ListUnansweredQueriesQuery(period=WINDOW, pagination=Pagination(limit=2)),
    )
    second = await list_unanswered_handler.handle(
        ListUnansweredQueriesQuery(
            period=WINDOW,
            pagination=Pagination(limit=2, offset=2),
        ),
    )

    first_texts = [query.text for query in first.queries]
    second_texts = [query.text for query in second.queries]
    assert len(first_texts) == len(second_texts) == 2
    assert set(first_texts).isdisjoint(second_texts)


async def test_ascending_order_surfaces_the_rarest_gaps_first(
    list_unanswered_handler: ListUnansweredQueriesHandler,
    analytics: InMemoryAnalytics,
) -> None:
    analytics.logs.extend(
        [
            make_query_log("asked once", results_count=0),
            make_query_log("asked twice", results_count=0),
            make_query_log("asked twice", results_count=0),
        ],
    )

    response = await list_unanswered_handler.handle(
        ListUnansweredQueriesQuery(period=WINDOW, sorting_order=SortingOrder.ASC),
    )

    assert [query.text for query in response.queries] == ["asked once", "asked twice"]


def test_a_period_cannot_end_before_it_starts() -> None:
    now = datetime.now(UTC)

    with pytest.raises(Exception, match="cannot precede"):
        Period(start=now, end=now - timedelta(days=1))
