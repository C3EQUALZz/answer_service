from collections import deque

from answer_service.domain.common.events_collection import EventsCollection
from answer_service.infrastructure.mappers import AdaptixQAPairDocumentMapper
from tests.unit.factories.domain_factories import make_qa_content, make_qa_pair


def test_the_pairs_identity_becomes_the_documents_external_id() -> None:
    """``QAPair.id`` and ``IndexDocument.external_id`` are the same value, renamed.

    The point id Qdrant stores is derived from this field, so losing the rename
    would scatter every pair across a different point than the one the
    projector later overwrites.
    """
    mapper = AdaptixQAPairDocumentMapper()
    pair = make_qa_pair("faq-1", EventsCollection(events=deque()))

    document = mapper.to_document(pair)

    assert document.external_id == pair.id


def test_nested_content_is_flattened_to_plain_text() -> None:
    mapper = AdaptixQAPairDocumentMapper()
    pair = make_qa_pair(
        "faq-1",
        EventsCollection(events=deque()),
        content=make_qa_content(question="Q?", answer="A.", category="billing"),
    )

    document = mapper.to_document(pair)

    assert document.question == "Q?"
    assert document.answer == "A."
    assert document.category == "billing"
