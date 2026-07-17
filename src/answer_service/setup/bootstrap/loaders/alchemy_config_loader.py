from typing import TYPE_CHECKING, Final, override

from dature import V, load

from answer_service.setup.bootstrap.loaders.loader import ConfigLoader
from answer_service.setup.configs.alchemy_config import SQLAlchemyConfig
from answer_service.setup.configs.consts import (
    POOL_OVERFLOW_MIN,
    POOL_RECYCLE_MIN,
    POOL_SIZE_MAX,
    POOL_SIZE_MIN,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dature.validators.root import RootPredicate

    from answer_service.setup.bootstrap.sources.source_factory import SourceFactory


class SQLAlchemyConfigLoader(ConfigLoader[SQLAlchemyConfig]):
    def __init__(self, source_factory: SourceFactory) -> None:
        self._source_factory: Final[SourceFactory] = source_factory

    @override
    def load(self) -> SQLAlchemyConfig:
        return load(
            self._source_factory.create(),
            schema=SQLAlchemyConfig,
            root_validators=self._root_validators(),
        )

    @staticmethod
    def _root_validators() -> Iterable[RootPredicate]:
        return (
            V.root(
                lambda c: c.pool_recycle >= POOL_RECYCLE_MIN,
                error_message=(
                    f"DB_POOL_RECYCLE must be at least {POOL_RECYCLE_MIN} minutes"
                ),
            ),
            V.root(
                lambda c: POOL_SIZE_MIN <= c.pool_size <= POOL_SIZE_MAX,
                error_message=(
                    f"DB_POOL_SIZE must be between {POOL_SIZE_MIN} and {POOL_SIZE_MAX}"
                ),
            ),
            V.root(
                lambda c: c.max_overflow >= POOL_OVERFLOW_MIN,
                error_message=(
                    f"DB_POOL_MAX_OVERFLOW must be at least {POOL_OVERFLOW_MIN}"
                ),
            ),
        )
