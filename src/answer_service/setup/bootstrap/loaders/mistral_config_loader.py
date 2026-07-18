from typing import TYPE_CHECKING, Final, override

from dature import V, load

from answer_service.setup.bootstrap.loaders.loader import ConfigLoader
from answer_service.setup.configs.mistral_config import MistralConfig

from .consts import TEMPERATURE_MAX, TEMPERATURE_MIN

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dature.validators.root import RootPredicate

    from answer_service.setup.bootstrap.sources.source_factory import SourceFactory


class MistralConfigLoader(ConfigLoader[MistralConfig]):
    """``dature``-backed loader for :class:`MistralConfig`."""

    def __init__(self, source_factory: SourceFactory) -> None:
        self._source_factory: Final[SourceFactory] = source_factory

    @override
    def load(self) -> MistralConfig:
        return load(
            self._source_factory.create(),
            schema=MistralConfig,
            root_validators=self._root_validators(),
            secret_field_names=("api_key",),
        )

    @staticmethod
    def _root_validators() -> Iterable[RootPredicate]:
        return (
            V.root(
                lambda c: bool(c.api_key.strip()),
                error_message="MISTRAL_API_KEY must not be empty",
            ),
            V.root(
                lambda c: c.embedding_dimension > 0,
                error_message="MISTRAL_EMBEDDING_DIMENSION must be positive",
            ),
            V.root(
                lambda c: TEMPERATURE_MIN <= c.temperature <= TEMPERATURE_MAX,
                error_message=(
                    f"MISTRAL_TEMPERATURE must be between"
                    f" {TEMPERATURE_MIN} and {TEMPERATURE_MAX}"
                ),
            ),
            V.root(
                lambda c: c.max_concurrency > 0,
                error_message="MISTRAL_MAX_CONCURRENCY must be positive",
            ),
        )
