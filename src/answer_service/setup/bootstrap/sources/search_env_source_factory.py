from typing import TYPE_CHECKING, override

from dature import EnvSource, F

from answer_service.setup.bootstrap.sources.source_factory import SourceFactory
from answer_service.setup.configs.search_config import SearchConfig

if TYPE_CHECKING:
    from dature.sources.protocol import SourceProtocol


class SearchEnvSourceFactory(SourceFactory):
    """Maps ``SEARCH_*`` environment variables onto :class:`SearchConfig`."""

    @override
    def create(self) -> SourceProtocol:
        return EnvSource(
            field_mapping={
                F[SearchConfig].dense_score_floor: "SEARCH_DENSE_SCORE_FLOOR",
                F[SearchConfig].lexical_relative_floor: "SEARCH_LEXICAL_RELATIVE_FLOOR",
                F[SearchConfig].lexical_absolute_floor: "SEARCH_LEXICAL_ABSOLUTE_FLOOR",
            },
        )
