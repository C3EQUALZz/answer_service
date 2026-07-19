"""The ask endpoint, through the real application.

The chat model is a fake with a fixed reply — what it writes is not what these
tests are about. What they are about is everything around it: that retrieval,
generation and recording happen in one dispatch, that an empty catalog does not
reach the model, and that one question produces exactly one row in the reports.
"""

import pytest
from httpx import AsyncClient

from tests.integration.arrange import PairBuilder, PairStorer
from tests.integration.ioc import FAKE_ANSWER

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.usefixtures("clean_tables"),
]

ASK_URL = "/v1/ask/"
STATISTICS_URL = "/v1/statistics/"
UNANSWERED_URL = "/v1/statistics/unanswered"


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
async def test_a_question_is_answered_with_its_sources(client: AsyncClient) -> None:
    response = await client.post(ASK_URL, json={"query": "reset password"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == FAKE_ANSWER
    assert body["query"] == "reset password"
    assert "q-password" in {source["external_id"] for source in body["sources"]}


@pytest.mark.usefixtures("_catalog")
async def test_every_source_carries_the_text_behind_it(client: AsyncClient) -> None:
    """A citation a caller cannot read is not a citation."""
    response = await client.post(ASK_URL, json={"query": "reset password"})

    sources = {source["external_id"]: source for source in response.json()["sources"]}
    assert sources["q-password"]["question"] == "How do I reset my password?"
    assert sources["q-password"]["category"] == "Account"


async def test_an_empty_catalog_yields_no_answer_rather_than_an_invented_one(
    client: AsyncClient,
) -> None:
    """The safeguard, end to end: nothing retrieved must reach no model."""
    response = await client.post(ASK_URL, json={"query": "anything at all"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] is None
    assert body["sources"] == []


@pytest.mark.usefixtures("_catalog")
async def test_a_category_filter_narrows_what_the_answer_may_draw_on(
    client: AsyncClient,
) -> None:
    response = await client.post(
        ASK_URL,
        json={"query": "reset password", "category": "Shipping"},
    )

    cited = {source["external_id"] for source in response.json()["sources"]}
    assert "q-password" not in cited


async def test_a_blank_question_is_rejected(client: AsyncClient) -> None:
    """Blank passes the schema's length check and is caught by the value object."""
    response = await client.post(ASK_URL, json={"query": "   "})

    assert response.status_code == 400


async def test_a_top_k_out_of_range_is_rejected(client: AsyncClient) -> None:
    response = await client.post(ASK_URL, json={"query": "hello", "top_k": 999})

    assert response.status_code == 422


@pytest.mark.usefixtures("_catalog")
async def test_one_question_is_counted_once(client: AsyncClient) -> None:
    """The reason asking is one dispatch.

    Retrieval used to be a second trip through the mediator, which the recording
    pipeline would have journalled as a search of its own — one user question,
    two rows, and a query volume that reads double.
    """
    await client.post(ASK_URL, json={"query": "reset password"})

    body = (await client.get(STATISTICS_URL)).json()

    assert body["queries"]["total"] == 1
    assert body["queries"]["answered"] == 1


async def test_a_question_nothing_answered_becomes_a_gap_report_entry(
    client: AsyncClient,
) -> None:
    """An unanswerable question is the entry the report exists to surface."""
    await client.post(ASK_URL, json={"query": "how do I cancel my subscription"})

    body = (await client.get(UNANSWERED_URL)).json()

    assert body["total_occurrences"] == 1
    assert [entry["text"] for entry in body["queries"]] == [
        "how do I cancel my subscription",
    ]
