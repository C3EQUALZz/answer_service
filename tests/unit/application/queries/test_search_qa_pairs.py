"""Hybrid search: two retrievers, one ranking, text joined from the catalog.

The handler is where the two halves meet, and the failure modes are quiet ones
— a result ranked but not returned, or returned with somebody else's text.
"""

import pytest

from answer_service.application.queries.search.search_qa_pairs.handler import (
    SearchQAPairsHandler,
)
from answer_service.application.queries.search.search_qa_pairs.query import (
    SearchQAPairsQuery,
)
from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.search.value_objects.score import Score
from answer_service.domain.search.value_objects.scored_candidate import ScoredCandidate
from answer_service.domain.search.value_objects.search_criteria import SearchCriteria
from answer_service.domain.search.value_objects.search_query import SearchQuery
from answer_service.domain.search.value_objects.top_k import TopK
from tests.unit.factories.domain_factories import make_qa_content, make_qa_pair
from tests.unit.stubs.gateways import InMemoryQACatalog
from tests.unit.stubs.infrastructure import StubDenseRetriever, StubLexicalRetriever


def make_query(
    text: str = "how do I reset my password",
    top_k: int = 5,
) -> SearchQAPairsQuery:
    return SearchQAPairsQuery(
        criteria=SearchCriteria(
            query=SearchQuery(content=text),
            top_k=TopK(value=top_k),
        ),
    )


def candidate(external_id: str, score: float) -> ScoredCandidate:
    return ScoredCandidate(
        external_id=ExternalId(value=external_id),
        score=Score(value=score),
    )


@pytest.fixture(autouse=True)
async def _seeded_catalog(
    catalog: InMemoryQACatalog,
    events_collection: EventsCollection,
) -> None:
    """Every test here searches over the same three pairs."""
    for external_id in ("q-1", "q-2", "q-3"):
        await catalog.add(
            make_qa_pair(
                external_id,
                events_collection,
                make_qa_content(
                    question=f"Question {external_id}?",
                    answer=f"Answer {external_id}.",
                    category="account",
                ),
            ),
        )


async def test_a_pair_only_one_retriever_found_still_reaches_the_ranking(
    dense_retriever: StubDenseRetriever,
    lexical_retriever: StubLexicalRetriever,
    search_qa_pairs_handler: SearchQAPairsHandler,
) -> None:
    """Running two retrievers is pointless if the union is not taken."""
    dense_retriever.candidates = [candidate("q-1", 0.9)]
    lexical_retriever.candidates = [candidate("q-2", 0.4)]

    response = await search_qa_pairs_handler.handle(make_query())

    assert {hit.pair.external_id for hit in response.hits} == {"q-1", "q-2"}


async def test_a_pair_both_retrievers_found_outranks_one_either_found_alone(
    dense_retriever: StubDenseRetriever,
    lexical_retriever: StubLexicalRetriever,
    search_qa_pairs_handler: SearchQAPairsHandler,
) -> None:
    """Agreement between two independent retrievers is the strongest signal."""
    dense_retriever.candidates = [candidate("q-1", 0.9), candidate("q-2", 0.8)]
    lexical_retriever.candidates = [candidate("q-3", 0.7), candidate("q-2", 0.6)]

    response = await search_qa_pairs_handler.handle(make_query())

    assert response.hits[0].pair.external_id == "q-2"
    assert response.hits[0].result.rank == 1


async def test_each_hit_carries_the_text_of_its_own_pair(
    dense_retriever: StubDenseRetriever,
    lexical_retriever: StubLexicalRetriever,
    search_qa_pairs_handler: SearchQAPairsHandler,
) -> None:
    """A misaligned join returns plausible nonsense rather than failing."""
    dense_retriever.candidates = [candidate("q-3", 0.9), candidate("q-1", 0.5)]
    lexical_retriever.candidates = []

    response = await search_qa_pairs_handler.handle(make_query())

    for hit in response.hits:
        assert hit.pair.question == f"Question {hit.pair.external_id}?"
        assert hit.pair.answer == f"Answer {hit.pair.external_id}."


async def test_the_score_breakdown_says_which_retriever_found_what(
    dense_retriever: StubDenseRetriever,
    lexical_retriever: StubLexicalRetriever,
    search_qa_pairs_handler: SearchQAPairsHandler,
) -> None:
    dense_retriever.candidates = [candidate("q-1", 0.9)]
    lexical_retriever.candidates = [candidate("q-2", 0.4)]

    response = await search_qa_pairs_handler.handle(make_query())
    by_id = {hit.pair.external_id: hit.result.scores for hit in response.hits}

    assert by_id["q-1"].dense is not None
    assert by_id["q-1"].lexical is None
    assert by_id["q-2"].dense is None
    assert by_id["q-2"].lexical is not None


async def test_a_pair_deleted_after_ranking_is_dropped_rather_than_returned_hollow(
    dense_retriever: StubDenseRetriever,
    lexical_retriever: StubLexicalRetriever,
    search_qa_pairs_handler: SearchQAPairsHandler,
) -> None:
    """The vector store lags the catalog, so it ranks pairs that are gone."""
    dense_retriever.candidates = [candidate("q-1", 0.9), candidate("q-gone", 0.8)]
    lexical_retriever.candidates = []

    response = await search_qa_pairs_handler.handle(make_query())

    assert [hit.pair.external_id for hit in response.hits] == ["q-1"]


async def test_ranks_are_consecutive_from_one(
    dense_retriever: StubDenseRetriever,
    lexical_retriever: StubLexicalRetriever,
    search_qa_pairs_handler: SearchQAPairsHandler,
) -> None:
    dense_retriever.candidates = [candidate("q-1", 0.9), candidate("q-2", 0.8)]
    lexical_retriever.candidates = [candidate("q-3", 0.7)]

    response = await search_qa_pairs_handler.handle(make_query())

    assert [hit.result.rank for hit in response.hits] == [1, 2, 3]


async def test_finding_nothing_is_an_empty_answer_not_an_error(
    dense_retriever: StubDenseRetriever,
    lexical_retriever: StubLexicalRetriever,
    search_qa_pairs_handler: SearchQAPairsHandler,
) -> None:
    """This is the case the gap report is built on; it must be ordinary."""
    dense_retriever.candidates = []
    lexical_retriever.candidates = []

    response = await search_qa_pairs_handler.handle(make_query())

    assert response.is_empty
    assert response.top_score is None


async def test_no_more_than_top_k_results_come_back(
    dense_retriever: StubDenseRetriever,
    lexical_retriever: StubLexicalRetriever,
    search_qa_pairs_handler: SearchQAPairsHandler,
) -> None:
    dense_retriever.candidates = [candidate("q-1", 0.9), candidate("q-2", 0.8)]
    lexical_retriever.candidates = [candidate("q-3", 0.7)]

    response = await search_qa_pairs_handler.handle(make_query(top_k=2))

    assert len(response.hits) == 2
