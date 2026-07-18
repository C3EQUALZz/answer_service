import pytest

from answer_service.domain.search.services.rrf_fusion import DEFAULT_RRF_K, RrfFusion
from answer_service.domain.search.value_objects.score import Score
from answer_service.domain.search.value_objects.top_k import TopK
from tests.unit.factories.domain_factories import make_scored_candidates
from tests.unit.support import ranked_external_ids


def test_no_candidates_produce_no_results(fusion: RrfFusion) -> None:
    assert fusion.fuse(dense=[], lexical=[], top_k=TopK(value=5)) == ()


def test_a_single_retriever_keeps_its_order(fusion: RrfFusion) -> None:
    results = fusion.fuse(
        dense=make_scored_candidates(("a", 0.9), ("b", 0.8), ("c", 0.7)),
        lexical=[],
        top_k=TopK(value=5),
    )

    assert ranked_external_ids(results) == ["a", "b", "c"]
    assert [result.rank for result in results] == [1, 2, 3]


def test_ranks_are_one_based_and_contiguous(fusion: RrfFusion) -> None:
    results = fusion.fuse(
        dense=make_scored_candidates(("a", 0.9), ("b", 0.8)),
        lexical=make_scored_candidates(
            ("c", 5.0),
        ),
        top_k=TopK(value=10),
    )

    assert [result.rank for result in results] == [1, 2, 3]


def test_a_pair_found_by_both_retrievers_outranks_one_found_by_either(
    fusion: RrfFusion,
) -> None:
    """The whole point of fusion: agreement between retrievers is evidence."""
    results = fusion.fuse(
        dense=make_scored_candidates(("only-dense", 0.99), ("both", 0.5)),
        lexical=make_scored_candidates(("only-lexical", 99.0), ("both", 0.1)),
        top_k=TopK(value=5),
    )

    assert ranked_external_ids(results)[0] == "both"


def test_fusion_ignores_the_scale_of_raw_scores(fusion: RrfFusion) -> None:
    """Lexical scores are unbounded, dense are cosine — only rank may matter.

    If raw scores leaked into the ranking, the lexical hit with score 1000 would
    dominate purely because of its scale.
    """
    modest = fusion.fuse(
        dense=make_scored_candidates(("a", 0.9)),
        lexical=make_scored_candidates(("b", 1.0)),
        top_k=TopK(value=5),
    )
    inflated = fusion.fuse(
        dense=make_scored_candidates(("a", 0.9)),
        lexical=make_scored_candidates(("b", 1000.0)),
        top_k=TopK(value=5),
    )

    assert ranked_external_ids(modest) == ranked_external_ids(inflated)


def test_the_contribution_matches_the_rrf_formula(fusion: RrfFusion) -> None:
    results = fusion.fuse(
        dense=make_scored_candidates(("a", 0.9)),
        lexical=make_scored_candidates(("a", 0.4)),
        top_k=TopK(value=1),
    )

    expected = 2 * (1.0 / (DEFAULT_RRF_K + 1))
    assert results[0].scores.final.value == pytest.approx(expected)


def test_the_original_scores_are_carried_through(fusion: RrfFusion) -> None:
    results = fusion.fuse(
        dense=make_scored_candidates(("a", 0.9)),
        lexical=make_scored_candidates(("a", 0.4), ("b", 0.3)),
        top_k=TopK(value=5),
    )
    by_id = {result.external_id.value: result for result in results}

    assert by_id["a"].scores.dense == Score(value=0.9)
    assert by_id["a"].scores.lexical == Score(value=0.4)
    assert by_id["b"].scores.dense is None
    assert by_id["b"].scores.lexical == Score(value=0.3)


def test_top_k_truncates_the_ranking(fusion: RrfFusion) -> None:
    results = fusion.fuse(
        dense=make_scored_candidates(("a", 0.9), ("b", 0.8), ("c", 0.7)),
        lexical=[],
        top_k=TopK(value=2),
    )

    assert ranked_external_ids(results) == ["a", "b"]


def test_ties_break_on_external_id_so_results_are_stable(fusion: RrfFusion) -> None:
    """Two pairs at the same rank in one retriever score identically.

    Without a deterministic tiebreak the order would follow set iteration and
    could differ between two identical requests.
    """
    first = fusion.fuse(
        dense=make_scored_candidates(("b", 1.0)),
        lexical=make_scored_candidates(("a", 1.0)),
        top_k=TopK(value=5),
    )
    second = fusion.fuse(
        dense=make_scored_candidates(("b", 1.0)),
        lexical=make_scored_candidates(("a", 1.0)),
        top_k=TopK(value=5),
    )

    assert ranked_external_ids(first) == ["a", "b"]
    assert ranked_external_ids(first) == ranked_external_ids(second)


def test_a_smaller_k_sharpens_the_advantage_of_the_top_rank() -> None:
    """K controls how much a top-ranked hit outweighs the ones below it."""
    dense = make_scored_candidates(("a", 0.9), ("b", 0.8))

    flat = RrfFusion(k=1000).fuse(dense=dense, lexical=[], top_k=TopK(value=2))
    sharp = RrfFusion(k=1).fuse(dense=dense, lexical=[], top_k=TopK(value=2))

    flat_gap = flat[0].scores.final.value - flat[1].scores.final.value
    sharp_gap = sharp[0].scores.final.value - sharp[1].scores.final.value
    assert sharp_gap > flat_gap


def test_a_candidate_present_twice_in_one_retriever_keeps_its_best_position() -> None:
    """A retriever should not repeat a candidate, but must not be punished if it does.

    Taking the later position would score a duplicated top hit *below* a
    single-occurrence hit ranked under it.
    """
    fusion = RrfFusion()

    results = fusion.fuse(
        dense=make_scored_candidates(("a", 0.9), ("a", 0.1), ("b", 0.5)),
        lexical=[],
        top_k=TopK(value=5),
    )

    assert ranked_external_ids(results) == ["a", "b"]
    assert results[0].scores.final.value == pytest.approx(1.0 / (DEFAULT_RRF_K + 1))
    assert results[0].scores.dense == Score(value=0.9)
