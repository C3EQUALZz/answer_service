import logging
from typing import Any, Final

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from answer_service.infrastructure.adapters.langchain.batch_token_estimator import (
    create_batch_token_estimator,
)
from answer_service.setup.configs.mistral_config import MistralConfig
from answer_service.setup.configs.qdrant_config import QdrantConfig

logger: Final[logging.Logger] = logging.getLogger(__name__)


def create_embedding_function(config: MistralConfig) -> Embeddings:
    """Creates the LangChain embeddings used for indexing and querying."""
    kwargs: dict[str, Any] = {
        "api_key": config.api_key,
        "model": config.embedding_model,
        "max_concurrent_requests": config.max_concurrency,
        "tokenizer": create_batch_token_estimator(),
    }
    if config.base_url:
        kwargs["endpoint"] = config.base_url
    return MistralAIEmbeddings(**kwargs)


def create_chat_model(config: MistralConfig) -> BaseChatModel:
    """Creates the chat model that generates grounded answers."""
    kwargs: dict[str, Any] = {
        "api_key": config.api_key,
        "model": config.chat_model,
        "temperature": config.temperature,
    }
    if config.base_url:
        kwargs["endpoint"] = config.base_url
    return ChatMistralAI(**kwargs)


def create_qdrant_client(config: QdrantConfig) -> QdrantClient:
    """Creates the Qdrant client.

    A sync client is enough: ``QdrantVectorStore`` inherits its ``a*`` methods
    from LangChain's base ``VectorStore``, which runs the sync call in an
    executor. The event loop stays free either way, and a second async client
    would only add a connection pool nobody reads from.
    """
    return QdrantClient(
        url=config.url,
        api_key=config.api_key or None,
        prefer_grpc=config.prefer_grpc,
    )


def ensure_collection(
    qdrant_client: QdrantClient,
    qdrant_config: QdrantConfig,
    mistral_config: MistralConfig,
) -> None:
    """Creates the collection on first start if it does not exist yet.

    The vector size is fixed at creation and cannot be altered afterwards, so it
    is taken from the same config the embedding model reads. Changing the
    embedding model therefore means recreating the collection, not just editing
    a variable — mismatched dimensions are rejected by Qdrant at insert time.
    """
    if qdrant_client.collection_exists(qdrant_config.collection_name):
        return

    logger.info("Creating Qdrant collection %s", qdrant_config.collection_name)
    qdrant_client.create_collection(
        collection_name=qdrant_config.collection_name,
        vectors_config=models.VectorParams(
            size=mistral_config.embedding_dimension,
            distance=models.Distance.COSINE,
        ),
    )


def create_qdrant_vectorstore(
    qdrant_config: QdrantConfig,
    mistral_config: MistralConfig,
    qdrant_client: QdrantClient,
    embedding_function: Embeddings,
) -> QdrantVectorStore:
    """Creates the vector store shared by the index writer and the retriever.

    Both sides take the same instance on purpose: it carries the embedding
    model, and two independently configured stores could drift onto different
    models, which produces silently poor results rather than an error.

    Ensures the collection first: the store validates it on construction, so
    without this a fresh deployment could not start. Constructing it does reach
    the server, which means the process refuses to start while Qdrant is
    unreachable — deliberate, since every write path depends on it.
    """
    ensure_collection(qdrant_client, qdrant_config, mistral_config)
    return QdrantVectorStore(
        client=qdrant_client,
        collection_name=qdrant_config.collection_name,
        embedding=embedding_function,
    )
