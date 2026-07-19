"""The request-journal endpoint, through the real application.

This is the §10 listing: one row per served request, with the filters the brief
enumerates. These tests prove the query parameters reach the handler and that
the rendered row carries the fields §9 requires — including the ``request_id``
the search and ask endpoints hand a caller to find their request here.
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from answer_service.domain.analytics.value_objects.error_code import ErrorCode
from answer_service.domain.analytics.value_objects.query_execution import QueryExecution
from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from tests.integration.arrange import QueryLogStorer

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.usefixtures("clean_tables"),
]

QUERIES_URL = "/v1/statistics/queries"
RECENTLY = datetime.now(UTC) - timedelta(hours=1)
FAILED = QueryExecution.failed(ErrorCode(value="SearchIndexError"))


async def test_a_recorded_request_is_listed_with_the_fields_the_brief_requires(
    client: AsyncClient,
    store_query_log: QueryLogStorer,
) -> None:
    await store_query_log(
        "how do I export data?",
        results_count=2,
        latency_ms=91,
        occurred_at=RECENTLY,
        category="technical",
        kind=QueryKind.SEARCH,
    )

    response = await client.get(QUERIES_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    (entry,) = body["entries"]
    assert entry["query"] == "how do I export data?"
    assert entry["kind"] == "search"
    assert entry["results_count"] == 2
    assert entry["duration_ms"] == 91
    assert entry["status"] == "succeeded"
    assert entry["error_code"] is None
    assert entry["category"] == "technical"
    # The identifier the caller was handed at search/ask time.
    assert entry["request_id"]


async def test_a_failed_request_is_listed_with_its_error_code(
    client: AsyncClient,
    store_query_log: QueryLogStorer,
) -> None:
    await store_query_log(
        "broke", results_count=0, occurred_at=RECENTLY, execution=FAILED
    )

    response = await client.get(QUERIES_URL)

    (entry,) = response.json()["entries"]
    assert entry["status"] == "failed"
    assert entry["error_code"] == "SearchIndexError"


async def test_the_operation_filter_narrows_the_listing(
    client: AsyncClient,
    store_query_log: QueryLogStorer,
) -> None:
    await store_query_log("searched", occurred_at=RECENTLY, kind=QueryKind.SEARCH)
    await store_query_log("asked", occurred_at=RECENTLY, kind=QueryKind.ASK)

    response = await client.get(QUERIES_URL, params={"kind": "ask"})

    assert [e["query"] for e in response.json()["entries"]] == ["asked"]


async def test_the_success_filter_narrows_the_listing(
    client: AsyncClient,
    store_query_log: QueryLogStorer,
) -> None:
    await store_query_log("ok", occurred_at=RECENTLY)
    await store_query_log(
        "broke", results_count=0, occurred_at=RECENTLY, execution=FAILED
    )

    response = await client.get(QUERIES_URL, params={"query_status": "failed"})

    entries = response.json()["entries"]
    assert [e["query"] for e in entries] == ["broke"]


async def test_the_listing_pages(
    client: AsyncClient,
    store_query_log: QueryLogStorer,
) -> None:
    for index in range(4):
        await store_query_log(
            f"q-{index}",
            occurred_at=RECENTLY - timedelta(minutes=index),
        )

    first = await client.get(QUERIES_URL, params={"limit": 2})
    second = await client.get(QUERIES_URL, params={"limit": 2, "offset": 2})

    first_ids = [e["request_id"] for e in first.json()["entries"]]
    second_ids = [e["request_id"] for e in second.json()["entries"]]
    assert len(first_ids) == len(second_ids) == 2
    assert set(first_ids).isdisjoint(second_ids)
    assert first.json()["total"] == 4


async def test_ascending_order_lists_oldest_first(
    client: AsyncClient,
    store_query_log: QueryLogStorer,
) -> None:
    await store_query_log("older", occurred_at=RECENTLY - timedelta(hours=1))
    await store_query_log("newer", occurred_at=RECENTLY)

    response = await client.get(QUERIES_URL, params={"sorting_order": "ASC"})

    assert [e["query"] for e in response.json()["entries"]] == ["older", "newer"]


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("limit", "0"),
        ("limit", "201"),
        ("offset", "-1"),
        ("days", "0"),
        ("kind", "browse"),
    ),
)
async def test_bad_parameters_are_rejected(
    field: str,
    value: str,
    client: AsyncClient,
) -> None:
    response = await client.get(QUERIES_URL, params={field: value})

    assert response.status_code == 422


async def test_an_empty_journal_is_not_an_error(client: AsyncClient) -> None:
    response = await client.get(QUERIES_URL)

    assert response.status_code == 200
    assert response.json()["entries"] == []
    assert response.json()["total"] == 0
