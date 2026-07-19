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
                lambda c: c.lexical_score_floor >= 0,
                error_message="SEARCH_LEXICAL_SCORE_FLOOR must not be negative",
            ),
        )
