"""The dense relevance floor, measured against known cosine similarities.

The shared integration fixtures embed with a deterministic *fake* model, whose
vectors are unrelated to meaning — a similarity against it says nothing, so a
floor cannot be tested through it. These tests therefore bring their own
embedding model, one that maps a handful of texts onto vectors chosen so the
cosine between any pair is arithmetic rather than incidental.

That is what makes the boundary assertable: a candidate sitting at exactly 0.8
is kept by a floor of 0.7 and dropped by one of 0.9, on identical data, with
nothing about the model left to luck.
"""

from typing import Final, override

import pytest
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from answer_service.domain.search.value_objects.search_criteria import SearchCriteria
from answer_service.domain.search.value_objects.search_query import SearchQuery
from answer_service.domain.search.value_objects.top_k import TopK
from answer_service.infrastructure.adapters.search import QdrantDenseRetriever
from answer_service.setup.configs.search_config import SearchConfig

pytestmark = [pytest.mark.asyncio(loop_scope="session")]

DIMENSION: Final[int] = 2

QUERY: Final[str] = "query"
EXACT: Final[str] = "exact"
CLOSE: Final[str] = "close"
DISTANT: Final[str] = "distant"

VECTORS: Final[dict[str, list[float]]] = {
    QUERY: [1.0, 0.0],
    EXACT: [1.0, 0.0],
    CLOSE: [0.8, 0.6],
    DISTANT: [0.0, 1.0],
}

COSINE_TO_QUERY: Final[dict[str, float]] = {
    EXACT: 1.0,
    CLOSE: 0.8,
    DISTANT: 0.0,
}


class PlannedEmbeddings(Embeddings):
    """Maps known texts onto vectors whose cosine to the query is known.

    Unknown text gets the query's own vector: the vector store probes the model
    with a throwaway string to discover its dimension, and that probe is never
    stored or searched.
    """

    @override
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [VECTORS.get(text, VECTORS[QUERY]) for text in texts]

    @override
    def embed_query(self, text: str) -> list[float]:
        return VECTORS.get(text, VECTORS[QUERY])


@pytest.fixture()
async def vector_store() -> QdrantVectorStore:
    """A collection of its own, so these vectors cannot disturb another test."""
    client = QdrantClient(location=":memory:")
    collection = "dense_floor_probe"
    client.create_collection(
        collection_name=collection,
        vectors_config=models.VectorParams(
            size=DIMENSION,
            distance=models.Distance.COSINE,
        ),
    )
    store = QdrantVectorStore(
        client=client,
        collection_name=collection,
        embedding=PlannedEmbeddings(),
    )
    await store.aadd_texts(
        texts=[EXACT, CLOSE, DISTANT],
        metadatas=[{"external_id": text} for text in (EXACT, CLOSE, DISTANT)],
    )
    return store


def retriever(store: QdrantVectorStore, floor: float) -> QdrantDenseRetriever:
    return QdrantDenseRetriever(store, SearchConfig(dense_score_floor=floor))


def criteria(top_k: int = 10) -> SearchCriteria:
    return SearchCriteria(query=SearchQuery(content=QUERY), top_k=TopK(value=top_k))


async def found_with(store: QdrantVectorStore, floor: float) -> set[str]:
    candidates = await retriever(store, floor).retrieve(criteria())
    return {candidate.external_id.value for candidate in candidates}


async def test_no_floor_returns_every_neighbour(
    vector_store: QdrantVectorStore,
) -> None:
    """Nearest-neighbour search always returns neighbours, however distant.

    This is the behaviour the floor exists to correct: without one, a question
    the catalog cannot answer still comes back looking answered.
    """
    assert await found_with(vector_store, 0.0) == {EXACT, CLOSE, DISTANT}


async def test_the_floor_drops_what_falls_below_it(
    vector_store: QdrantVectorStore,
) -> None:
    """0.8 is kept at a floor of 0.7 and dropped at 0.9, on the same data."""
    assert await found_with(vector_store, 0.7) == {EXACT, CLOSE}
    assert await found_with(vector_store, 0.9) == {EXACT}


async def test_the_production_floor_admits_a_close_match(
    vector_store: QdrantVectorStore,
) -> None:
    """The configured default has to keep a genuine neighbour, or search is blind."""
    assert EXACT in await found_with(vector_store, SearchConfig().dense_score_floor)


async def test_a_floor_above_everything_reports_nothing_found(
    vector_store: QdrantVectorStore,
) -> None:
    """The gap report is built on this: an empty result must be reachable."""
    assert await found_with(vector_store, 1.01) == set()


async def test_candidates_carry_the_similarity_the_vectors_imply(
    vector_store: QdrantVectorStore,
) -> None:
    """Fusion reports the dense score, so it must be the real cosine.

    Doubles as the guard on the fixture: if these vectors ever drift, every
    boundary asserted above stops meaning what it claims, and this fails first.
    """
    candidates = await retriever(vector_store, 0.0).retrieve(criteria())
    scores = {c.external_id.value: c.score.value for c in candidates}

    for text, expected in COSINE_TO_QUERY.items():
        assert scores[text] == pytest.approx(expected, abs=1e-6)
