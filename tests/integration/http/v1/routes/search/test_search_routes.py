"""The search endpoint, through the real application.

Both retrievers are real here: PostgreSQL full-text against the same rows the
catalog serves, and Qdrant in-process with deterministic embeddings. What the
dense half ranks is therefore arbitrary — these tests assert the contract, the
plumbing and the recording, and leave relevance to the retriever tests.
"""

from uuid import UUID

import pytest
from httpx import AsyncClient

from answer_service.application.commands.search.upsert_qa_pair.command import (
    UpsertQAPairCommand,
)
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from tests.integration.arrange import CommandSender, PairBuilder, PairStorer

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.usefixtures("clean_tables"),
]

SEARCH_URL = "/api/v1/search"
STATISTICS_URL = "/api/v1/statistics"
UNANSWERED_URL = "/api/v1/statistics/unanswered"


@pytest.fixture()
async def _catalog(
    clean_tables: None,
    make_pair: PairBuilder,
    store_qa_pairs: PairStorer,
) -> None:
    """Seeded after the truncation, which is why it depends on it explicitly."""
    del clean_tables
    await store_qa_pairs(
        make_pair(
            "q-password",
            question="How do I reset my password?",
            answer="Open settings and choose reset.",
            category="Account",
        ),
        make_pair(
            "q-shipping",
            question="How long does shipping take?",
            answer="Between three and five business days.",
            category="Shipping",
        ),
    )


@pytest.mark.usefixtures("_catalog")
async def test_a_search_returns_the_matching_pair_with_its_text(
    client: AsyncClient,
) -> None:
    response = await client.post(SEARCH_URL, json={"query": "reset password"})

    assert response.status_code == 200
    body = response.json()
    found = {result["external_id"]: result for result in body["results"]}
    assert "q-password" in found
    assert found["q-password"]["question"] == "How do I reset my password?"
    assert found["q-password"]["answer"] == "Open settings and choose reset."
    assert found["q-password"]["category"] == "Account"


@pytest.mark.usefixtures("_catalog")
async def test_results_are_ranked_from_one_without_gaps(
    client: AsyncClient,
) -> None:
    response = await client.post(SEARCH_URL, json={"query": "reset password"})

    ranks = [result["rank"] for result in response.json()["results"]]
    assert ranks == list(range(1, len(ranks) + 1))


@pytest.mark.usefixtures("_catalog")
async def test_the_response_says_which_retriever_found_each_hit(
    client: AsyncClient,
) -> None:
    """A hit with no lexical score came from the vector store alone."""
    response = await client.post(SEARCH_URL, json={"query": "reset password"})

    for result in response.json()["results"]:
        scores = result["scores"]
        assert scores["final"] > 0
        assert scores["dense"] is not None or scores["lexical"] is not None


@pytest.mark.usefixtures("_catalog")
async def test_top_k_bounds_the_response(client: AsyncClient) -> None:
    response = await client.post(
        SEARCH_URL,
        json={"query": "reset or shipping", "top_k": 1},
    )

    body = response.json()
    assert body["total"] == 1
    assert len(body["results"]) == 1


async def test_searching_an_empty_catalog_is_an_empty_answer(
    client: AsyncClient,
) -> None:
    """The gap report is built on this case, so it must not be an error."""
    response = await client.post(SEARCH_URL, json={"query": "anything at all"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["results"] == []


async def test_a_blank_query_is_rejected(client: AsyncClient) -> None:
    """Blank passes the schema's length check and is caught by the value object.

    400 rather than 422 because it is the domain refusing the value, which is
    the split the exception mapping already draws.
    """
    response = await client.post(SEARCH_URL, json={"query": "   "})

    assert response.status_code == 400


async def test_a_top_k_out_of_range_is_rejected(client: AsyncClient) -> None:
    """Rejected by the schema before a request scope is even opened."""
    response = await client.post(SEARCH_URL, json={"query": "hello", "top_k": 999})

    assert response.status_code == 422


@pytest.mark.usefixtures("_catalog")
async def test_a_served_search_reaches_the_statistics(
    client: AsyncClient,
) -> None:
    """Recording is what makes the reporting endpoints mean anything."""
    await client.post(SEARCH_URL, json={"query": "reset password"})

    body = (await client.get(STATISTICS_URL)).json()

    assert body["queries"]["total"] == 1
    assert body["queries"]["answered"] == 1
    assert body["queries"]["unanswered"] == 0


@pytest.mark.usefixtures("_catalog")
async def test_the_response_carries_a_request_id_and_a_duration(
    client: AsyncClient,
) -> None:
    response = await client.post(SEARCH_URL, json={"query": "reset password"})

    body = response.json()
    assert UUID(body["request_id"])
    assert isinstance(body["duration_ms"], int)


@pytest.mark.usefixtures("_catalog")
async def test_the_returned_request_id_is_the_one_the_journal_kept(
    client: AsyncClient,
) -> None:
    """The correlation the id exists for: a caller finds their own request.

    The value handed back by the search endpoint must be the identity the
    listing pages under, or the id would point at nothing.
    """
    request_id = (await client.post(SEARCH_URL, json={"query": "reset password"})).json()[
        "request_id"
    ]

    listed = (await client.get("/api/v1/statistics/queries")).json()["entries"]

    assert [entry["request_id"] for entry in listed] == [request_id]


async def test_a_search_that_found_nothing_becomes_a_gap_report_entry(
    client: AsyncClient,
) -> None:
    """The whole point of the report: this is an FAQ entry worth writing."""
    await client.post(SEARCH_URL, json={"query": "how do I cancel my subscription"})

    body = (await client.get(UNANSWERED_URL)).json()

    assert body["total_occurrences"] == 1
    assert [entry["text"] for entry in body["queries"]] == [
        "how do I cancel my subscription",
    ]


@pytest.mark.usefixtures("_catalog")
async def test_a_projected_pair_is_found_by_both_halves(
    client: AsyncClient,
    send_command: CommandSender,
) -> None:
    """The one test where hybrid actually means two retrievers, not one.

    Everything above runs against an empty vector store, so the lexical half
    carries it alone. Projecting first is what puts the pair in Qdrant, and the
    score breakdown is then the proof both retrievers found it.
    """
    await send_command(
        UpsertQAPairCommand(external_id=ExternalId(value="q-password")),
    )

    response = await client.post(SEARCH_URL, json={"query": "reset password"})

    found = {result["external_id"]: result for result in response.json()["results"]}
    assert found["q-password"]["scores"]["dense"] is not None
    assert found["q-password"]["scores"]["lexical"] is not None
