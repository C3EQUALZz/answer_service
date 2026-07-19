from typing import Annotated, Self

from pydantic import BaseModel, Field

from answer_service.application.common.services import SearchHit
from answer_service.application.queries.search.search_qa_pairs.query import (
    SearchQAPairsResponse,
)
from answer_service.domain.search.value_objects.top_k import MAX_TOP_K, MIN_TOP_K
from answer_service.presentation.http.v1.common.schemas import CriteriaRequest

DEFAULT_TOP_K: int = 5


class SearchRequest(CriteriaRequest):
    """What to look for and how much of it to return."""

    top_k: Annotated[
        int,
        Field(
            ge=MIN_TOP_K,
            le=MAX_TOP_K,
            description="How many results to return",
        ),
    ] = DEFAULT_TOP_K


class ScoresSchema(BaseModel):
    """The score breakdown behind a result.

    Both halves are reported so a caller can tell *why* something ranked: a hit
    with only a lexical score matched words the embedding missed, and vice
    versa.
    """

    final: float
    dense: float | None
    lexical: float | None


class SearchResultSchema(BaseModel):
    external_id: str
    rank: int
    question: str
    answer: str
    category: str
    scores: ScoresSchema

    @classmethod
    def of(cls, hit: SearchHit) -> Self:
        scores = hit.result.scores
        return cls(
            external_id=hit.pair.external_id,
            rank=hit.result.rank,
            question=hit.pair.question,
            answer=hit.pair.answer,
            category=hit.pair.category,
            scores=ScoresSchema(
                final=scores.final.value,
                dense=scores.dense.value if scores.dense is not None else None,
                lexical=scores.lexical.value if scores.lexical is not None else None,
            ),
        )


class SearchSchemaResponse(BaseModel):
    """The ranking, best first."""

    query: str
    total: int
    took_ms: int
    results: list[SearchResultSchema]

    @classmethod
    def of(cls, response: SearchQAPairsResponse, took_ms: int) -> Self:
        return cls(
            query=response.query.content,
            total=len(response.hits),
            took_ms=took_ms,
            results=[SearchResultSchema.of(hit) for hit in response.hits],
        )
