from answer_service.application.common.ports.search import IndexDocument
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.infrastructure.adapters.search.qdrant_dense_retriever import (
    EXTERNAL_ID_METADATA_KEY,
)
from answer_service.infrastructure.mappers import AdaptixIndexMetadataMapper


def _document() -> IndexDocument:
    return IndexDocument(
        external_id=ExternalId(value="faq-1"),
        question="Q?",
        answer="A.",
        category="billing",
    )


def test_the_external_id_is_written_under_the_key_the_retriever_reads() -> None:
    """The writer and the dense retriever must agree on this key.

    They are two files apart: the retriever looks the id up by name to build
    its candidates, so a payload written under any other key returns hits the
    fusion step cannot resolve back to a pair.
    """
    mapper = AdaptixIndexMetadataMapper()

    metadata = mapper.to_metadata(_document())

    assert metadata[EXTERNAL_ID_METADATA_KEY] == "faq-1"


def test_the_external_id_is_flattened_to_a_plain_string() -> None:
    """Qdrant stores JSON; a value object would not survive the round trip."""
    mapper = AdaptixIndexMetadataMapper()

    metadata = mapper.to_metadata(_document())

    assert isinstance(metadata[EXTERNAL_ID_METADATA_KEY], str)


def test_every_document_field_reaches_the_payload() -> None:
    mapper = AdaptixIndexMetadataMapper()

    metadata = mapper.to_metadata(_document())

    assert metadata == {
        "external_id": "faq-1",
        "question": "Q?",
        "answer": "A.",
        "category": "billing",
    }
