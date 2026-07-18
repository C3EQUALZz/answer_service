from collections import deque
from datetime import UTC, datetime, timedelta

from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.entities.qa_pair import QAPair
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from tests.unit.factories.domain_factories import SOURCE_UPDATED_AT, make_qa_content


def make_pair() -> tuple[QAPair, EventsCollection]:
    collection = EventsCollection(events=deque())
    pair = QAPair.register(
        external_id=ExternalId(value="q-1"),
        content=make_qa_content(),
        source_updated_at=SOURCE_UPDATED_AT,
        events_collection=collection,
    )
    return pair, collection


def emitted(collection: EventsCollection) -> list[str]:
    return [type(event).__name__ for event in collection.pull_events()]


def test_registering_announces_the_pair() -> None:
    pair, collection = make_pair()

    assert pair.id == ExternalId(value="q-1")
    assert emitted(collection) == ["QAPairAdded"]


def test_a_pair_matches_its_own_fingerprint() -> None:
    pair, _ = make_pair()

    assert pair.matches(pair.content.fingerprint)
    assert not pair.matches(make_qa_content(answer="different").fingerprint)


def test_updating_with_new_content_reports_the_change() -> None:
    pair, collection = make_pair()
    emitted(collection)
    later = SOURCE_UPDATED_AT + timedelta(days=1)

    changed = pair.update_content(
        content=make_qa_content(answer="A newer answer."),
        source_updated_at=later,
    )

    assert changed
    assert pair.content.answer.content == "A newer answer."
    assert pair.source_updated_at == later
    assert emitted(collection) == ["QAPairContentUpdated"]


def test_updating_with_identical_content_is_a_no_op() -> None:
    """Re-running an unchanged file must not touch the pair or the index."""
    pair, collection = make_pair()
    emitted(collection)
    before = pair.updated_at

    changed = pair.update_content(
        content=make_qa_content(),
        source_updated_at=SOURCE_UPDATED_AT + timedelta(days=1),
    )

    assert not changed
    assert pair.updated_at == before
    assert pair.source_updated_at == SOURCE_UPDATED_AT
    assert emitted(collection) == []


def test_a_real_update_stamps_updated_at() -> None:
    pair, _ = make_pair()
    before = pair.updated_at

    pair.update_content(
        content=make_qa_content(question="A different question?"),
        source_updated_at=datetime.now(UTC),
    )

    assert pair.updated_at >= before


def test_removal_announces_itself() -> None:
    """Without the event the pair would linger in the search index forever."""
    pair, collection = make_pair()
    emitted(collection)

    pair.mark_removed()

    assert emitted(collection) == ["QAPairRemoved"]
