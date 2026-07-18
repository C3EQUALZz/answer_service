from typing import TYPE_CHECKING, override

from dature import EnvSource, F

from answer_service.setup.bootstrap.sources.source_factory import SourceFactory
from answer_service.setup.configs.mistral_config import MistralConfig

if TYPE_CHECKING:
    from dature.sources.protocol import SourceProtocol


class MistralEnvSourceFactory(SourceFactory):
    """Maps ``MISTRAL_*`` environment variables onto :class:`MistralConfig`."""

    @override
    def create(self) -> SourceProtocol:
        return EnvSource(
            field_mapping={
                F[MistralConfig].api_key: "MISTRAL_API_KEY",
                F[MistralConfig].base_url: "MISTRAL_BASE_URL",
                F[MistralConfig].embedding_model: "MISTRAL_EMBEDDING_MODEL",
                F[MistralConfig].embedding_dimension: "MISTRAL_EMBEDDING_DIMENSION",
                F[MistralConfig].chat_model: "MISTRAL_CHAT_MODEL",
                F[MistralConfig].temperature: "MISTRAL_TEMPERATURE",
                F[MistralConfig].max_concurrency: "MISTRAL_MAX_CONCURRENCY",
            },
        )
