from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MistralConfig:
    """Settings for the Mistral models used for embeddings and generation.

    Plain stdlib dataclass with no dependency on the config loader: the env
    mapping and validation live in
    ``answer_service.setup.bootstrap.loaders.mistral_config_loader``.

    Attributes:
        api_key: Mistral API key.
        base_url: Custom API endpoint, empty to use the official one.
        embedding_model: Model producing the dense vectors for search.
        embedding_dimension: Vector width the model emits. Must match the
            Qdrant collection, which is created with a fixed size.
        chat_model: Model generating the RAG answers.
        temperature: Sampling temperature for generation. Kept at zero by
            default: an answer grounded in retrieved documents should be
            reproducible rather than creative.
        max_concurrency: Parallel embedding requests allowed during indexing.
        embedding_timeout_seconds: Ceiling on one embedding request. Bounds the
            query embedding on the search path and each batch during indexing;
            the SDK's own default is 120s, far too long for a user waiting on a
            search.
        chat_timeout_seconds: Ceiling on one chat completion, for the RAG
            answer. Larger than the embedding ceiling because a generation is
            slower than an embedding, still well under the SDK's 120s default.
    """

    api_key: str
    base_url: str = ""
    embedding_model: str = "mistral-embed"
    embedding_dimension: int = 1024
    chat_model: str = "mistral-large-latest"
    temperature: float = 0.0
    max_concurrency: int = 5
    embedding_timeout_seconds: int = 30
    chat_timeout_seconds: int = 60
