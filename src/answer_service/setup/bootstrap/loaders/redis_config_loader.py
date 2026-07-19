from typing import TYPE_CHECKING, Final, override

from dature import V, load

from answer_service.setup.bootstrap.loaders.loader import ConfigLoader
from answer_service.setup.configs.redis_config import RedisConfig

from .consts import PORT_MAX, PORT_MIN, REDIS_DB_MAX, REDIS_DB_MIN

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dature.validators.root import RootPredicate

    from answer_service.setup.bootstrap.sources.source_factory import SourceFactory


class RedisConfigLoader(ConfigLoader[RedisConfig]):
    """``dature``-backed loader for :class:`RedisConfig`."""

    def __init__(self, source_factory: SourceFactory) -> None:
        self._source_factory: Final[SourceFactory] = source_factory

    @override
    def load(self) -> RedisConfig:
        return load(
            self._source_factory.create(),
            schema=RedisConfig,
            root_validators=self._root_validators(),
            secret_field_names=("password",),
        )

    @staticmethod
    def _root_validators() -> Iterable[RootPredicate]:
        db_range = f"must be between {REDIS_DB_MIN} and {REDIS_DB_MAX}"
        return (
            V.root(
                lambda c: PORT_MIN <= c.port <= PORT_MAX,
                error_message=f"REDIS_PORT must be between {PORT_MIN} and {PORT_MAX}",
            ),
            V.root(
                lambda c: not c.user or bool(c.password),
                error_message=(
                    "REDIS_USER requires REDIS_PASSWORD: an ACL user without a "
                    "password cannot authenticate"
                ),
            ),
            V.root(
                lambda c: REDIS_DB_MIN <= c.worker_db <= REDIS_DB_MAX,
                error_message=f"REDIS_WORKER_DB {db_range}",
            ),
            V.root(
                lambda c: REDIS_DB_MIN <= c.schedule_source_db <= REDIS_DB_MAX,
                error_message=f"REDIS_SCHEDULE_SOURCE_DB {db_range}",
            ),
            V.root(
                lambda c: REDIS_DB_MIN <= c.cache_db <= REDIS_DB_MAX,
                error_message=f"REDIS_CACHE_DB {db_range}",
            ),
            V.root(
                lambda c: len({c.worker_db, c.schedule_source_db, c.cache_db}) == 3,  # ruff:ignore[magic-value-comparison]
                error_message=(
                    "REDIS_WORKER_DB, REDIS_SCHEDULE_SOURCE_DB and REDIS_CACHE_DB "
                    "must be three different database indexes"
                ),
            ),
        )
