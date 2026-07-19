from typing import TYPE_CHECKING, Final, override

from dature import V, load

from answer_service.setup.bootstrap.loaders.loader import ConfigLoader
from answer_service.setup.configs.indexing_config import IndexingConfig

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dature.validators.root import RootPredicate

    from answer_service.setup.bootstrap.sources.source_factory import SourceFactory

MIN_STUCK_AFTER_SECONDS: Final[int] = 60


class IndexingConfigLoader(ConfigLoader[IndexingConfig]):
    """``dature``-backed loader for :class:`IndexingConfig`."""

    def __init__(self, source_factory: SourceFactory) -> None:
        self._source_factory: Final[SourceFactory] = source_factory

    @override
    def load(self) -> IndexingConfig:
        return load(
            self._source_factory.create(),
            schema=IndexingConfig,
            root_validators=self._root_validators(),
        )

    @staticmethod
    def _root_validators() -> Iterable[RootPredicate]:
        """Refuses a threshold short enough to reap live work.

        A minute is already implausibly tight for a sync, and anything below it
        would let the reaper fail runs that are simply in progress — turning a
        safeguard into the outage it exists to prevent.
        """
        return (
            V.root(
                lambda c: c.stuck_after_seconds >= MIN_STUCK_AFTER_SECONDS,
                error_message=(
                    "INDEXING_STUCK_AFTER_SECONDS must be at least "
                    f"{MIN_STUCK_AFTER_SECONDS}; a shorter one reaps running work"
                ),
            ),
        )
