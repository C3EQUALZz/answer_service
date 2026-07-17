from typing import TYPE_CHECKING, Final, override

from dature import V, load

from answer_service.setup.bootstrap.loaders.loader import ConfigLoader
from answer_service.setup.configs.asgi_config import ASGIConfig

from .consts import PORT_MAX, PORT_MIN

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dature.validators.root import RootPredicate

    from answer_service.setup.bootstrap.sources.source_factory import SourceFactory


class ASGIConfigLoader(ConfigLoader[ASGIConfig]):
    """``dature``-backed loader for :class:`ASGIConfig`.

    Backend-agnostic: the concrete :class:`SourceFactory` is injected in the DI
    container, so the source is chosen there without touching this class.
    """

    def __init__(self, source_factory: SourceFactory) -> None:
        self._source_factory: Final[SourceFactory] = source_factory

    @override
    def load(self) -> ASGIConfig:
        return load(
            self._source_factory.create(),
            schema=ASGIConfig,
            root_validators=self._root_validators(),
        )

    @staticmethod
    def _root_validators() -> Iterable[RootPredicate]:
        return (
            V.root(
                lambda c: PORT_MIN <= c.port <= PORT_MAX,
                error_message=f"UVICORN_PORT must be between {PORT_MIN} and {PORT_MAX}",
            ),
        )
