from typing import TYPE_CHECKING, Final, override

from dature import V, load

from answer_service.setup.bootstrap.loaders.loader import ConfigLoader
from answer_service.setup.configs.consts import PORT_MAX, PORT_MIN
from answer_service.setup.configs.postgres_config import PostgresConfig

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dature.validators.root import RootPredicate

    from answer_service.setup.bootstrap.sources.source_factory import SourceFactory


class PostgresConfigLoader(ConfigLoader[PostgresConfig]):
    """``dature``-backed loader for :class:`PostgresConfig`.

    Backend-agnostic: the concrete :class:`SourceFactory` (env, TOML, YAML,
    Vault...) is injected, so switching source is a wiring decision made in the
    DI container, never a change to this class.
    """

    def __init__(self, source_factory: SourceFactory) -> None:
        self._source_factory: Final[SourceFactory] = source_factory

    @override
    def load(self) -> PostgresConfig:
        return load(
            self._source_factory.create(),
            schema=PostgresConfig,
            root_validators=self._root_validators(),
            secret_field_names=("password",),
        )

    @staticmethod
    def _root_validators() -> Iterable[RootPredicate]:
        # Root validators run against the fully-built dataclass, so they are
        # independent of which source the value came from.
        return (
            V.root(
                lambda c: PORT_MIN <= c.port <= PORT_MAX,
                error_message=f"POSTGRES_PORT must be between {PORT_MIN} and {PORT_MAX}",
            ),
        )
