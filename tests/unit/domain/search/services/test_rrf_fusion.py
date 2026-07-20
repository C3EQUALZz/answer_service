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


def test_the_default_is_plain_unweighted_fusion() -> None:
    """The tuned ratio belongs to configuration; the domain default is neutral."""
    results = RrfFusion().fuse(
        dense=make_scored_candidates(("a", 0.9)),
        lexical=make_scored_candidates(("b", 5.0)),
        top_k=TopK(value=2),
    )

    expected = pytest.approx(1.0 / (DEFAULT_RRF_K + 1))
    assert results[0].scores.final.value == expected
    assert results[1].scores.final.value == expected


def test_weighting_a_retriever_up_lets_it_win_a_disagreement() -> None:
    """What the weights exist for, stated as the case that motivated them.

    Each retriever ranks its own pick first and neither returns the other's, so
    unweighted fusion ties them and the ordering falls to ``external_id``. That
    tie is what cost top-1 accuracy on natural questions, where the lexical side
    ranks on shared vocabulary alone.
    """
    dense = make_scored_candidates(("z-dense-pick", 0.9))
    lexical = make_scored_candidates(("a-lexical-pick", 5.0))

    balanced = RrfFusion().fuse(dense=dense, lexical=lexical, top_k=TopK(value=2))
    dense_led = RrfFusion(dense_weight=2.0).fuse(
        dense=dense,
        lexical=lexical,
        top_k=TopK(value=2),
    )

    assert balanced[0].external_id.value == "a-lexical-pick"
    assert balanced[0].scores.final.value == pytest.approx(
        balanced[1].scores.final.value,
    )
    assert dense_led[0].external_id.value == "z-dense-pick"
    assert dense_led[0].scores.final.value > dense_led[1].scores.final.value


def test_weighting_cannot_admit_a_candidate_neither_retriever_returned() -> None:
    """Weights reorder what cleared the floors; they are not a second floor."""
    results = RrfFusion(dense_weight=100.0, lexical_weight=0.01).fuse(
        dense=make_scored_candidates(("a", 0.9)),
        lexical=make_scored_candidates(("b", 5.0)),
        top_k=TopK(value=10),
    )

    assert sorted(result.external_id.value for result in results) == ["a", "b"]
