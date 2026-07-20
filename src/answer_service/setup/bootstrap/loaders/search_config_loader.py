from typing import TYPE_CHECKING, Final, override

from dature import V, load

from answer_service.setup.bootstrap.loaders.loader import ConfigLoader
from answer_service.setup.configs.search_config import SearchConfig

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dature.validators.root import RootPredicate

    from answer_service.setup.bootstrap.sources.source_factory import SourceFactory

MIN_COSINE: Final[float] = -1.0
MAX_COSINE: Final[float] = 1.0

MIN_RATIO: Final[float] = 0.0
MAX_RATIO: Final[float] = 1.0

MIN_RANK: Final[float] = 0.0

MIN_WEIGHT: Final[float] = 0.0


class SearchConfigLoader(ConfigLoader[SearchConfig]):
    """``dature``-backed loader for :class:`SearchConfig`."""

    def __init__(self, source_factory: SourceFactory) -> None:
        self._source_factory: Final[SourceFactory] = source_factory

    @override
    def load(self) -> SearchConfig:
        return load(
            self._source_factory.create(),
            schema=SearchConfig,
            root_validators=self._root_validators(),
        )

    @staticmethod
    def _root_validators() -> Iterable[RootPredicate]:
        return (
            V.root(
                lambda c: MIN_COSINE <= c.dense_score_floor <= MAX_COSINE,
                error_message=(
                    "SEARCH_DENSE_SCORE_FLOOR is a cosine similarity and must be "
                    f"between {MIN_COSINE} and {MAX_COSINE}"
                ),
            ),
            V.root(
                lambda c: MIN_RATIO <= c.lexical_relative_floor <= MAX_RATIO,
                error_message=(
                    "SEARCH_LEXICAL_RELATIVE_FLOOR is a fraction of the best "
                    f"match and must be between {MIN_RATIO} and {MAX_RATIO}"
                ),
            ),
            V.root(
                lambda c: c.lexical_absolute_floor >= MIN_RANK,
                error_message=(
                    "SEARCH_LEXICAL_ABSOLUTE_FLOOR is a ts_rank_cd value and must "
                    f"be at least {MIN_RANK}"
                ),
            ),
            V.root(
                lambda c: c.dense_weight > MIN_WEIGHT and c.lexical_weight > MIN_WEIGHT,
                error_message=(
                    "SEARCH_DENSE_WEIGHT and SEARCH_LEXICAL_WEIGHT scale a "
                    f"retriever's say in the ranking and must be above {MIN_WEIGHT}; "
                    "a retriever is silenced by its floor, not by its weight"
                ),
            ),
        )
