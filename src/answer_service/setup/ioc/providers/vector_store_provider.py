from typing import Final

from dishka import Provider, Scope
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from answer_service.setup.ioc.providers.langchain_provider import (
    create_chat_model,
    create_embedding_function,
    create_qdrant_client,
    create_qdrant_vectorstore,
)


def vector_store_provider() -> Provider:
    """Embedding model, Qdrant client and vector store, all process-wide.

    All ``APP`` scope: each holds a connection pool or a tokenizer that is
    expensive to build and safe to share, and one shared vector store is what
    keeps the writer and the retriever on the same embedding model.
    """
    provider: Final[Provider] = Provider(scope=Scope.APP)
    provider.provide(create_embedding_function, provides=Embeddings)
    provider.provide(create_chat_model, provides=BaseChatModel)
    provider.provide(create_qdrant_client, provides=QdrantClient)
    provider.provide(create_qdrant_vectorstore, provides=QdrantVectorStore)
    return provider
