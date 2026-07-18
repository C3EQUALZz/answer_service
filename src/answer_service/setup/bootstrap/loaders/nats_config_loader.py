from typing import TYPE_CHECKING, Final, override

from dature import V, load

from answer_service.setup.bootstrap.loaders.loader import ConfigLoader
from answer_service.setup.configs.nats_config import NatsConfig

from .consts import PORT_MAX, PORT_MIN

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dature.validators.root import RootPredicate

    from answer_service.setup.bootstrap.sources.source_factory import SourceFactory


class NatsConfigLoader(ConfigLoader[NatsConfig]):
    """``dature``-backed loader for :class:`NatsConfig`."""

    def __init__(self, source_factory: SourceFactory) -> None:
        self._source_factory: Final[SourceFactory] = source_factory

    @override
    def load(self) -> NatsConfig:
        return load(
            self._source_factory.create(),
            schema=NatsConfig,
            root_validators=self._root_validators(),
            secret_field_names=("password",),
        )

    @staticmethod
    def _root_validators() -> Iterable[RootPredicate]:
        return (
            V.root(
                lambda c: PORT_MIN <= c.port <= PORT_MAX,
                error_message=f"NATS_PORT must be between {PORT_MIN} and {PORT_MAX}",
            ),
        )
