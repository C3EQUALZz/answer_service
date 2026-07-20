"""Does the search actually find the right answer?

Everything else in this suite checks that the machinery works: rows move, events
relay, floors filter, contracts hold. None of it can tell you whether a person
typing a question gets the entry that answers it, because the shared fixtures
embed with a fake model whose similarities carry no meaning.

So this runs against a real deployment — real embedding model, real Qdrant, real
PostgreSQL full-text — and measures two things a passing unit test cannot:

* how often the right pair is found, over questions worded as a person would
  word them rather than as the catalog words them;
* how often the catalog correctly refuses, over questions it cannot answer.

The second is the one that catches drift no exception ever will. A retriever
that answers everything looks healthy in every other test in this repository,
and quietly empties the gap report the product is built to produce.

Skipped unless a stack is reachable, so it never blocks a change that has no
deployment to test against. Point it elsewhere with QUALITY_BASE_URL.
"""

import os
from collections.abc import Iterator
from typing import Final

import httpx
import pytest

from tests.quality.dataset import (
    MIN_REFUSED,
    MIN_TOP_1,
    MIN_TOP_3,
    OFF_TOPIC,
    PARAPHRASED,
)

pytestmark = pytest.mark.quality

BASE_URL: Final[str] = os.getenv("QUALITY_BASE_URL", "http://localhost:8080")
TIMEOUT: Final[float] = 60.0
TOP_K: Final[int] = 3
EXPECTED_PAIRS: Final[int] = 40


@pytest.fixture(scope="session")
def client() -> Iterator[httpx.Client]:
    """A client against a live deployment, or a skip explaining what is missing.

    ``trust_env`` is off because httpx otherwise routes through ``HTTP_PROXY``,
    and a proxy set for outbound traffic swallows requests to a deployment on
    localhost — which surfaces as read timeouts and 503s that look like the
    service failing rather than the client never reaching it.
    """
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT, trust_env=False) as http:
        try:
            http.get("/healthcheck/").raise_for_status()
        except httpx.HTTPError as error:
            pytest.skip(f"no deployment at {BASE_URL}: {error}")

        catalog = http.get("/api/v1/statistics").json()["catalog"]
        if catalog["total_pairs"] < EXPECTED_PAIRS:
            pytest.skip(
                f"{BASE_URL} holds {catalog['total_pairs']} pair(s); upload "
                f"examples/qa_catalog_sample.xlsx first",
            )
        yield http


def search(client: httpx.Client, query: str) -> list[str]:
    response = client.post("/api/v1/search", json={"query": query, "top_k": TOP_K})
    response.raise_for_status()
    return [hit["external_id"] for hit in response.json()["results"]]


def report(title: str, misses: list[str], rate: float, floor: float) -> str:
    lines = [f"{title}: {rate:.0%} (floor {floor:.0%})", *misses]
    return "\n".join(lines)


def test_a_paraphrased_question_finds_its_pair(client: httpx.Client) -> None:
    """Top-1 accuracy over questions worded the way a person would word them."""
    misses: list[str] = []
    hits = 0

    for query, expected in PARAPHRASED:
        found = search(client, query)
        if found[:1] == [expected]:
            hits += 1
        else:
            misses.append(f"  {query!r} -> {found or ['nothing']}, wanted {expected}")

    rate = hits / len(PARAPHRASED)
    assert rate >= MIN_TOP_1, report("top-1", misses, rate, MIN_TOP_1)


def test_the_right_pair_is_at_least_offered(client: httpx.Client) -> None:
    """Top-3 accuracy: ask grounds on several pairs, so being in the set counts."""
    misses: list[str] = []
    hits = 0

    for query, expected in PARAPHRASED:
        found = search(client, query)
        if expected in found:
            hits += 1
        else:
            misses.append(f"  {query!r} -> {found or ['nothing']}, wanted {expected}")

    rate = hits / len(PARAPHRASED)
    assert rate >= MIN_TOP_3, report("top-3", misses, rate, MIN_TOP_3)


def test_a_question_the_catalog_cannot_answer_returns_nothing(
    client: httpx.Client,
) -> None:
    """The half no other test covers, and the half that decays silently.

    A match here is not a wrong answer so much as a lie about coverage: the
    query is journalled as answered and never reaches the gap report, so the
    missing FAQ entry is never written.
    """
    answered: list[str] = []
    refused = 0

    for query in OFF_TOPIC:
        found = search(client, query)
        if found:
            answered.append(f"  {query!r} -> {found}")
        else:
            refused += 1

    rate = refused / len(OFF_TOPIC)
    assert rate >= MIN_REFUSED, report("refused", answered, rate, MIN_REFUSED)


def test_an_unanswerable_question_is_declined_rather_than_improvised(
    client: httpx.Client,
) -> None:
    """``/api/v1/ask`` must return a null answer, not prose saying it does not know.

    A caller cannot branch on prose. If the model is reached at all with nothing
    relevant, the safeguard has already failed — the null is what says so.
    """
    improvised: list[str] = []

    for query in OFF_TOPIC:
        response = client.post("/api/v1/ask", json={"query": query})
        response.raise_for_status()
        body = response.json()
        if body["answer"] is not None:
            improvised.append(f"  {query!r} -> {body['answer'][:70]!r}")

    declined = len(OFF_TOPIC) - len(improvised)
    rate = declined / len(OFF_TOPIC)
    assert rate >= MIN_REFUSED, report("declined", improvised, rate, MIN_REFUSED)
