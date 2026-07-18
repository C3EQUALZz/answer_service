import math

import pytest

from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.search.errors import (
    EmptyCategoryFilterError,
    EmptySearchQueryError,
    InvalidRankError,
    InvalidScoreError,
    SearchQueryTooLongError,
    TopKOutOfRangeError,
)
from answer_service.domain.search.value_objects.category_filter import CategoryFilter
from answer_service.domain.search.value_objects.ranked_result import RankedResult
from answer_service.domain.search.value_objects.result_scores import Scores
from answer_service.domain.search.value_objects.score import Score
from answer_service.domain.search.value_objects.search_criteria import SearchCriteria
from answer_service.domain.search.value_objects.search_outcome import SearchOutcome
from answer_service.domain.search.value_objects.search_query import (
    MAX_QUERY_LENGTH,
    SearchQuery,
)
from answer_service.domain.search.value_objects.top_k import MAX_TOP_K, MIN_TOP_K, TopK


def test_a_query_must_have_content() -> None:
    with pytest.raises(EmptySearchQueryError):
        SearchQuery(content="   ")


def test_a_query_at_the_limit_is_accepted() -> None:
    assert SearchQuery(content="q" * MAX_QUERY_LENGTH)

    with pytest.raises(SearchQueryTooLongError):
        SearchQuery(content="q" * (MAX_QUERY_LENGTH + 1))


@pytest.mark.parametrize("value", (MIN_TOP_K, MAX_TOP_K))
def test_top_k_accepts_its_bounds(value: int) -> None:
    assert TopK(value=value).value == value


@pytest.mark.parametrize("value", (MIN_TOP_K - 1, MAX_TOP_K + 1, -5))
def test_top_k_rejects_values_outside_its_bounds(value: int) -> None:
    """An unbounded top_k lets a single request pull the whole index."""
    with pytest.raises(TopKOutOfRangeError):
        TopK(value=value)


def test_a_category_filter_must_name_something() -> None:
    with pytest.raises(EmptyCategoryFilterError):
        CategoryFilter(value="")


@pytest.mark.parametrize("value", (math.inf, -math.inf, math.nan))
def test_a_non_finite_score_is_rejected(value: float) -> None:
    """NaN would leave the ranking sort order undefined."""
    with pytest.raises(InvalidScoreError):
        Score(value=value)


@pytest.mark.parametrize("value", (0.0, -1.5, 1e9))
def test_any_finite_score_is_accepted(value: float) -> None:
    """Lexical scores are unbounded and dense ones may be negative."""
    assert Score(value=value).value == value


def test_criteria_may_omit_the_category() -> None:
    criteria = SearchCriteria(
        query=SearchQuery(content="how do I reset my password?"),
        top_k=TopK(value=5),
    )

    assert criteria.category is None


def test_a_rank_starts_at_one() -> None:
    scores = Scores(final=Score(value=0.5))

    assert RankedResult(external_id=ExternalId(value="q-1"), rank=1, scores=scores)

    with pytest.raises(InvalidRankError):
        RankedResult(external_id=ExternalId(value="q-1"), rank=0, scores=scores)


def test_scores_may_come_from_one_retriever_only() -> None:
    scores = Scores(final=Score(value=0.1), dense=Score(value=0.9))

    assert scores.lexical is None


def test_an_outcome_knows_when_it_found_nothing() -> None:
    query = SearchQuery(content="anything at all")

    assert SearchOutcome(query=query, results=()).is_empty
    assert not SearchOutcome(
        query=query,
        results=(
            RankedResult(
                external_id=ExternalId(value="q-1"),
                rank=1,
                scores=Scores(final=Score(value=0.5)),
            ),
        ),
    ).is_empty
