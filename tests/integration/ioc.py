"""Providers for integration tests.

Everything the service is built from is reused verbatim — the point of these
tests is that the real wiring works. Only the two providers that reach outside
the test's control are swapped:

* the vector store, which would need a running Qdrant and a paid embedding API;
* the chat model, for the same reason.

Postgres, NATS-less taskiq and the whole application layer stay real.
"""

from collections.abc import Iterable
from typing import Final

from dishka import Provider, Scope
from langchain_core.embeddings import DeterministicFakeEmbedding, Embeddings
from langchain_core.language_models import BaseChatModel, FakeListChatModel
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from answer_service.setup.configs.qdrant_config import QdrantConfig
from answer_service.setup.ioc.providers import (
    configs_provider,
    database_provider,
    domain_provider,
    gateways_provider,
    handlers_provider,
    mediator_provider,
    pipelines_provider,
    services_provider,
    task_manager_provider,
)

EMBEDDING_DIMENSION: Final[int] = 8

FAKE_ANSWER: Final[str] = "A grounded answer."


def create_fake_embeddings() -> Embeddings:
    """Deterministic vectors, so a test can assert on what was indexed."""
    return DeterministicFakeEmbedding(size=EMBEDDING_DIMENSION)


def create_fake_chat_model() -> BaseChatModel:
    return FakeListChatModel(responses=[FAKE_ANSWER])


def create_in_memory_qdrant_client() -> QdrantClient:
    """Qdrant's in-process mode: the real client and real filtering, no server."""
    return QdrantClient(location=":memory:")


def create_test_qdrant_vectorstore(
    qdrant_config: QdrantConfig,
    qdrant_client: QdrantClient,
    embedding_function: Embeddings,
) -> QdrantVectorStore:
    """Mirrors the production factory, sized for the fake embedding model."""
    if not qdrant_client.collection_exists(qdrant_config.collection_name):
        qdrant_client.create_collection(
            collection_name=qdrant_config.collection_name,
            vectors_config=models.VectorParams(
                size=EMBEDDING_DIMENSION,
                distance=models.Distance.COSINE,
            ),
        )
    return QdrantVectorStore(
        client=qdrant_client,
        collection_name=qdrant_config.collection_name,
        embedding=embedding_function,
    )


def test_vector_store_provider() -> Provider:
    provider: Final[Provider] = Provider(scope=Scope.APP)
    provider.provide(create_fake_embeddings, provides=Embeddings)
    provider.provide(create_fake_chat_model, provides=BaseChatModel)
    provider.provide(create_in_memory_qdrant_client, provides=QdrantClient)
    provider.provide(create_test_qdrant_vectorstore, provides=QdrantVectorStore)
    return provider


def test_app_providers() -> Iterable[Provider]:
    """The production provider set with the vector store swapped out."""
    return (
        configs_provider(),
        database_provider(),
        test_vector_store_provider(),
        task_manager_provider(),
        domain_provider(),
        gateways_provider(),
        pipelines_provider(),
        services_provider(),
        handlers_provider(),
        mediator_provider(),
    )
