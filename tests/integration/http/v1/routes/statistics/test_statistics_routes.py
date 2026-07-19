"""The statistics endpoints, through the real application.

The catalog half comes from the QA catalog and the query half from the log, so
these are the only tests that prove the two halves are assembled from the same
request and rendered as one document.
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.integration.arrange import PairBuilder, PairStorer, QueryLogStorer

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.usefixtures("clean_tables"),
]

STATISTICS_URL = "/api/v1/statistics"
UNANSWERED_URL = "/api/v1/statistics/unanswered"
RECENTLY = datetime.now(UTC) - timedelta(hours=1)


async def test_an_untouched_service_still_reports(client: AsyncClient) -> None:
    """The report must render before anything has been indexed or asked."""
    response = await client.get(STATISTICS_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["catalog"]["total_pairs"] == 0
    assert body["queries"]["total"] == 0
    assert body["queries"]["unanswered_rate"] == pytest.approx(0.0)
    assert body["popular_queries"] == []


async def test_the_report_counts_the_catalog(
    client: AsyncClient,
    make_pair: PairBuilder,
    store_qa_pairs: PairStorer,
) -> None:
    await store_qa_pairs(
        make_pair("q-1", category="billing"),
        make_pair("q-2", category="billing"),
        make_pair("q-3", category="account"),
    )

    response = await client.get(STATISTICS_URL)

    catalog = response.json()["catalog"]
    assert catalog["total_pairs"] == 3
    assert catalog["category_count"] == 2
    assert catalog["pairs_per_category"] == {"billing": 2, "account": 1}


async def test_the_report_counts_the_queries(
    client: AsyncClient,
    store_query_log: QueryLogStorer,
) -> None:
    await store_query_log(
        "answered", results_count=2, latency_ms=100, occurred_at=RECENTLY
    )
    await store_query_log("a gap", results_count=0, latency_ms=300, occurred_at=RECENTLY)

    response = await client.get(STATISTICS_URL)

    queries = response.json()["queries"]
    assert queries["total"] == 2
    assert queries["answered"] == 1
    assert queries["unanswered"] == 1
    assert queries["unanswered_rate"] == pytest.approx(0.5)
    assert queries["average_latency_ms"] == pytest.approx(200.0)


async def test_the_report_ranks_popular_queries(
    client: AsyncClient,
    store_query_log: QueryLogStorer,
) -> None:
    for _ in range(2):
        await store_query_log("asked twice", occurred_at=RECENTLY)
    await store_query_log("asked once", occurred_at=RECENTLY)

    response = await client.get(STATISTICS_URL)

    popular = response.json()["popular_queries"]
    assert popular[0] == {"text": "asked twice", "occurrences": 2}


async def test_the_period_narrows_the_query_half_only(
    client: AsyncClient,
    make_pair: PairBuilder,
    store_qa_pairs: PairStorer,
    store_query_log: QueryLogStorer,
) -> None:
    """A QA pair has no history, so the catalog is always reported as of now."""
    await store_qa_pairs(make_pair("q-1"))
    await store_query_log("recent", occurred_at=RECENTLY)
    await store_query_log(
        "ancient",
        occurred_at=datetime.now(UTC) - timedelta(days=90),
    )

    response = await client.get(STATISTICS_URL, params={"days": 7})

    body = response.json()
    assert body["queries"]["total"] == 1
    assert body["catalog"]["total_pairs"] == 1


@pytest.mark.parametrize("days", (0, -1, 366))
async def test_an_out_of_range_period_is_rejected(
    days: int,
    client: AsyncClient,
) -> None:
    response = await client.get(STATISTICS_URL, params={"days": days})

    assert response.status_code == 422


async def test_the_gap_report_lists_only_unanswered_queries(
    client: AsyncClient,
    store_query_log: QueryLogStorer,
) -> None:
    await store_query_log("how do I cancel?", results_count=0, occurred_at=RECENTLY)
    await store_query_log("how do I cancel?", results_count=0, occurred_at=RECENTLY)
    await store_query_log("answered fine", results_count=4, occurred_at=RECENTLY)

    response = await client.get(UNANSWERED_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["queries"] == [{"text": "how do I cancel?", "occurrences": 2}]
    assert body["total_occurrences"] == 2


async def test_the_gap_report_pages(
    client: AsyncClient,
    store_query_log: QueryLogStorer,
) -> None:
    for index in range(4):
        await store_query_log(f"gap-{index}", results_count=0, occurred_at=RECENTLY)

    first = await client.get(UNANSWERED_URL, params={"limit": 2})
    second = await client.get(UNANSWERED_URL, params={"limit": 2, "offset": 2})

    first_texts = [query["text"] for query in first.json()["queries"]]
    second_texts = [query["text"] for query in second.json()["queries"]]
    assert len(first_texts) == len(second_texts) == 2
    assert set(first_texts).isdisjoint(second_texts)


async def test_the_gap_report_can_surface_the_rarest_first(
    client: AsyncClient,
    store_query_log: QueryLogStorer,
) -> None:
    await store_query_log("rare", results_count=0, occurred_at=RECENTLY)
    for _ in range(2):
        await store_query_log("common", results_count=0, occurred_at=RECENTLY)

    response = await client.get(UNANSWERED_URL, params={"sorting_order": "ASC"})

    assert [query["text"] for query in response.json()["queries"]] == ["rare", "common"]


@pytest.mark.parametrize(
    ("field", "value"), (("limit", 0), ("limit", 201), ("offset", -1))
)
async def test_bad_paging_is_rejected(
    field: str,
    value: int,
    client: AsyncClient,
) -> None:
    response = await client.get(UNANSWERED_URL, params={field: value})

    assert response.status_code == 422


async def test_an_empty_gap_report_is_not_an_error(client: AsyncClient) -> None:
    """No gaps is the desirable state, not a missing resource."""
    response = await client.get(UNANSWERED_URL)

    assert response.status_code == 200
    assert response.json()["queries"] == []
    assert response.json()["total_occurrences"] == 0
