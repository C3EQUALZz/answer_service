import logging
from typing import TYPE_CHECKING, Final

from answer_service.domain.common.service import BaseDomainService
from answer_service.domain.search.value_objects.ranked_result import RankedResult
from answer_service.domain.search.value_objects.result_scores import Scores
from answer_service.domain.search.value_objects.score import Score

if TYPE_CHECKING:
    from collections.abc import Sequence

    from answer_service.domain.indexing.value_objects.external_id import ExternalId
    from answer_service.domain.search.value_objects.scored_candidate import (
        ScoredCandidate,
    )
    from answer_service.domain.search.value_objects.top_k import TopK

DEFAULT_RRF_K: int = 60
DEFAULT_DENSE_WEIGHT: float = 1.0
DEFAULT_LEXICAL_WEIGHT: float = 1.0


logger: Final[logging.Logger] = logging.getLogger(__name__)


class RrfFusion(BaseDomainService):
    """Reciprocal Rank Fusion of dense and lexical retrieval results.

    Each candidate contributes ``weight / (k + rank)`` per retriever it appears
    in (rank is 1-based position in that retriever's ordered list);
    contributions are summed into the final score. Fusion is rank-based, so it
    is immune to the differing score scales of the two retrievers.

    The weights exist because the two retrievers are not equally trustworthy on
    the input this service actually receives. Lexical terms are OR-ed, so a pair
    sharing one word of a natural question is ranked at all, and a pair the
    embedding model put first can be pushed down the fused list by pairs that
    merely share vocabulary. Weighting is the only lever for that: the floors
    decide *whether* a candidate competes, and this decides how much its
    position counts once it does.

    Ordering is deterministic: results are sorted by final score descending,
    ties broken by ``external_id`` ascending.
    """

    def __init__(
        self,
        k: int = DEFAULT_RRF_K,
        *,
        dense_weight: float = DEFAULT_DENSE_WEIGHT,
        lexical_weight: float = DEFAULT_LEXICAL_WEIGHT,
    ) -> None:
        self._k: Final[int] = k
        self._dense_weight: Final[float] = dense_weight
        self._lexical_weight: Final[float] = lexical_weight

    @staticmethod
    def _best_positions(
        candidates: Sequence[ScoredCandidate],
    ) -> dict[ExternalId, tuple[int, Score]]:
        """Indexes candidates by id, keeping the first occurrence of each.

        A retriever should not repeat a candidate, but if it does, the earlier
        position is the one it ranked higher — taking the later one would
        penalise a result for having been returned twice.
        """
        positions: dict[ExternalId, tuple[int, Score]] = {}
        for position, candidate in enumerate(candidates):
            if candidate.external_id not in positions:
                positions[candidate.external_id] = (position, candidate.score)
        return positions

    def fuse(
        self,
        *,
        dense: Sequence[ScoredCandidate],
        lexical: Sequence[ScoredCandidate],
        top_k: TopK,
    ) -> tuple[RankedResult, ...]:
        dense_by_id = self._best_positions(dense)
        lexical_by_id = self._best_positions(lexical)
        logger.debug(
            "rrf_fusion: fusing dense=%d (weight %.2f) lexical=%d (weight %.2f), "
            "k=%d, top_k=%d",
            len(dense_by_id),
            self._dense_weight,
            len(lexical_by_id),
            self._lexical_weight,
            self._k,
            top_k.value,
        )

        fused: list[tuple[ExternalId, Scores]] = []
        for external_id in dense_by_id.keys() | lexical_by_id.keys():
            dense_hit = dense_by_id.get(external_id)
            lexical_hit = lexical_by_id.get(external_id)

            contribution = 0.0
            if dense_hit is not None:
                contribution += self._dense_weight / (self._k + dense_hit[0] + 1)
            if lexical_hit is not None:
                contribution += self._lexical_weight / (self._k + lexical_hit[0] + 1)

            fused.append(
                (
                    external_id,
                    Scores(
                        final=Score(value=contribution),
                        dense=dense_hit[1] if dense_hit is not None else None,
                        lexical=lexical_hit[1] if lexical_hit is not None else None,
                    ),
                ),
            )

        fused.sort(key=lambda item: (-item[1].final.value, item[0].value))
        logger.debug(
            "rrf_fusion: %d unique candidate(s), returning %d",
            len(fused),
            min(len(fused), top_k.value),
        )

        return tuple(
            RankedResult(external_id=external_id, rank=position, scores=scores)
            for position, (external_id, scores) in enumerate(
                fused[: top_k.value],
                start=1,
            )
        )
