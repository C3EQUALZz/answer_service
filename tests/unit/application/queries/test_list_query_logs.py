"""The request-journal listing handler over the in-memory analytics stub.

The stub re-implements the gateway's filtering and paging in Python so a test
can state the expected rows directly; the SQL that must agree with it is pinned
by ``tests/integration/analytics``. Here the concern is the handler's own
decisions: the limit ceiling, and that the filters reach the gateway intact.
"""

from datetime import timedelta

import pytest

from answer_service.application.common.query_params.pagination import Pagination
from answer_service.application.common.query_params.sorting import SortingOrder
from answer_service.application.error import PaginationError
from answer_service.application.queries.analytics.list_query_logs.handler import (
    MAX_LIMIT,
    ListQueryLogsHandler,
)
from answer_service.application.queries.analytics.list_query_logs.query import (
    ListQueryLogsQuery,
)
from answer_service.domain.analytics.value_objects.error_code import ErrorCode
from answer_service.domain.analytics.value_objects.period import Period
from answer_service.domain.analytics.value_objects.query_execution import QueryExecution
from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from answer_service.domain.analytics.value_objects.query_status import QueryStatus
from tests.unit.factories.domain_factories import SOURCE_UPDATED_AT, make_query_log
from tests.unit.stubs.gateways import InMemoryAnalytics

WINDOW = Period(
    start=SOURCE_UPDATED_AT - timedelta(days=1),
    end=SOURCE_UPDATED_AT + timedelta(days=1),
)
FAILED = QueryExecution.failed(ErrorCode(value="SearchIndexError"))


async def test_every_matching_entry_is_returned_with_its_fields(
    list_query_logs_handler: ListQueryLogsHandler,
    analytics: InMemoryAnalytics,
) -> None:
    analytics.logs.append(
        make_query_log("how do I export data?", results_count=2, latency_ms=88),
    )

    response = await list_query_logs_handler.handle(ListQueryLogsQuery(period=WINDOW))

    (entry,) = response.entries
    assert entry.text == "how do I export data?"
    assert entry.results_count == 2
    assert entry.latency_ms == 88
    assert entry.status is QueryStatus.SUCCEEDED
    assert entry.error_code is None


async def test_a_failed_entry_reports_its_status_and_code(
    list_query_logs_handler: ListQueryLogsHandler,
    analytics: InMemoryAnalytics,
) -> None:
    analytics.logs.append(make_query_log("a", results_count=0, execution=FAILED))

    response = await list_query_logs_handler.handle(ListQueryLogsQuery(period=WINDOW))

    (entry,) = response.entries
    assert entry.status is QueryStatus.FAILED
    assert entry.error_code == "SearchIndexError"


async def test_the_kind_filter_narrows_to_one_operation(
    list_query_logs_handler: ListQueryLogsHandler,
    analytics: InMemoryAnalytics,
) -> None:
    analytics.logs.extend(
        [
            make_query_log("searched", kind=QueryKind.SEARCH),
            make_query_log("asked", kind=QueryKind.ASK),
        ],
    )

    response = await list_query_logs_handler.handle(
        ListQueryLogsQuery(period=WINDOW, kind=QueryKind.ASK),
    )

    assert [entry.text for entry in response.entries] == ["asked"]


async def test_the_status_filter_narrows_to_failures(
    list_query_logs_handler: ListQueryLogsHandler,
    analytics: InMemoryAnalytics,
) -> None:
    analytics.logs.extend(
        [
            make_query_log("ok"),
            make_query_log("broke", results_count=0, execution=FAILED),
        ],
    )

    response = await list_query_logs_handler.handle(
        ListQueryLogsQuery(period=WINDOW, status=QueryStatus.FAILED),
    )

    assert [entry.text for entry in response.entries] == ["broke"]


async def test_the_total_counts_matches_before_paging(
    list_query_logs_handler: ListQueryLogsHandler,
    analytics: InMemoryAnalytics,
) -> None:
    """``total`` tells a caller how far the pages go, so it ignores the page size."""
    analytics.logs.extend(make_query_log(f"q{i}") for i in range(5))

    response = await list_query_logs_handler.handle(
        ListQueryLogsQuery(period=WINDOW, pagination=Pagination(limit=2)),
    )

    assert len(response.entries) == 2
    assert response.total == 5


async def test_entries_outside_the_period_are_excluded(
    list_query_logs_handler: ListQueryLogsHandler,
    analytics: InMemoryAnalytics,
) -> None:
    analytics.logs.extend(
        [
            make_query_log("inside", occurred_at=SOURCE_UPDATED_AT),
            make_query_log(
                "before",
                occurred_at=SOURCE_UPDATED_AT - timedelta(days=30),
            ),
        ],
    )

    response = await list_query_logs_handler.handle(ListQueryLogsQuery(period=WINDOW))

    assert [entry.text for entry in response.entries] == ["inside"]
    assert response.total == 1


async def test_a_limit_over_the_ceiling_is_refused(
    list_query_logs_handler: ListQueryLogsHandler,
) -> None:
    """The journal is the highest-volume table; an unbounded page could pull it all."""
    query = ListQueryLogsQuery(
        period=WINDOW,
        pagination=Pagination(limit=MAX_LIMIT + 1),
    )

    with pytest.raises(PaginationError):
        await list_query_logs_handler.handle(query)


async def test_ascending_order_reaches_the_gateway(
    list_query_logs_handler: ListQueryLogsHandler,
    analytics: InMemoryAnalytics,
) -> None:
    """Order is over arrival time, so the caller can page oldest-first too."""
    analytics.logs.extend(
        [
            make_query_log("newer", occurred_at=SOURCE_UPDATED_AT),
            make_query_log(
                "older",
                occurred_at=SOURCE_UPDATED_AT - timedelta(hours=1),
            ),
        ],
    )

    response = await list_query_logs_handler.handle(
        ListQueryLogsQuery(period=WINDOW, sorting_order=SortingOrder.ASC),
    )

    assert [entry.text for entry in response.entries] == ["older", "newer"]
