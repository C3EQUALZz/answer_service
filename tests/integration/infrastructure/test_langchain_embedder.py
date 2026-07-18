"""What the adapter itself decides — not what the embedding model computes."""

from typing import override

from langchain_core.embeddings import Embeddings

from answer_service.infrastructure.adapters.langchain.langchain_embedder import (
    LangChainEmbedder,
)


class RecordingEmbeddings(Embeddings):
    """Records what the adapter asked the model for."""

    def __init__(self) -> None:
        self.document_calls: list[list[str]] = []
        self.query_calls: list[str] = []

    @override
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls.append(texts)
        return [[0.1] for _ in texts]

    @override
    def embed_query(self, text: str) -> list[float]:
        self.query_calls.append(text)
        return [0.1]


async def test_an_empty_batch_never_reaches_the_model() -> None:
    """A sync with no creates must not spend an API call on nothing."""
    model = RecordingEmbeddings()

    result = await LangChainEmbedder(model).embed_documents([])

    assert result == []
    assert model.document_calls == []


async def test_a_sequence_is_handed_over_as_a_list() -> None:
    """The port accepts any Sequence; the model requires a list."""
    model = RecordingEmbeddings()

    await LangChainEmbedder(model).embed_documents(("first", "second"))

    assert model.document_calls == [["first", "second"]]


async def test_queries_and_documents_use_different_model_calls() -> None:
    """Some models prefix queries differently; mixing the two degrades recall."""
    model = RecordingEmbeddings()
    embedder = LangChainEmbedder(model)

    await embedder.embed_query("a question")
    await embedder.embed_documents(["a document"])

    assert model.query_calls == ["a question"]
    assert model.document_calls == [["a document"]]
