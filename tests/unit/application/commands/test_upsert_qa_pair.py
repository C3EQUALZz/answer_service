from answer_service.application.commands.search.upsert_qa_pair.command import (
    UpsertQAPairCommand,
)
from answer_service.application.commands.search.upsert_qa_pair.handler import (
    UpsertQAPairHandler,
)
from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from tests.unit.factories.domain_factories import make_qa_content, make_qa_pair
from tests.unit.stubs.gateways import InMemoryQACatalog
from tests.unit.stubs.infrastructure import RecordingSearchIndexWriter


def make_command(external_id: str = "q-1") -> UpsertQAPairCommand:
    return UpsertQAPairCommand(external_id=ExternalId(value=external_id))


async def test_indexes_the_current_catalog_content(
    catalog: InMemoryQACatalog,
    events_collection: EventsCollection,
    index_writer: RecordingSearchIndexWriter,
    upsert_qa_pair_handler: UpsertQAPairHandler,
) -> None:
    await catalog.add(
        make_qa_pair(
            "q-1",
            events_collection,
            make_qa_content(question="How?", answer="Like this.", category="howto"),
        ),
    )

    await upsert_qa_pair_handler.handle(make_command())

    assert len(index_writer.upserted) == 1
    document = index_writer.upserted[0]
    assert document.external_id == ExternalId(value="q-1")
    assert document.question == "How?"
    assert document.answer == "Like this."
    assert document.category == "howto"


async def test_projection_reads_current_state_not_the_event(
    catalog: InMemoryQACatalog,
    events_collection: EventsCollection,
    index_writer: RecordingSearchIndexWriter,
    upsert_qa_pair_handler: UpsertQAPairHandler,
) -> None:
    """A replayed old event must not resurrect stale content."""
    await catalog.add(
        make_qa_pair(
            "q-1",
            events_collection,
            make_qa_content(answer="The newest answer."),
        ),
    )

    await upsert_qa_pair_handler.handle(make_command())

    assert index_writer.upserted[0].answer == "The newest answer."


async def test_a_pair_deleted_before_projection_is_skipped(
    index_writer: RecordingSearchIndexWriter,
    upsert_qa_pair_handler: UpsertQAPairHandler,
) -> None:
    """The removal event is already queued and will clear the entry."""
    await upsert_qa_pair_handler.handle(make_command("q-vanished"))

    assert index_writer.upserted == []
    assert index_writer.deleted == []


async def test_replaying_an_event_is_indistinguishable_from_applying_it_once(
    catalog: InMemoryQACatalog,
    events_collection: EventsCollection,
    index_writer: RecordingSearchIndexWriter,
    upsert_qa_pair_handler: UpsertQAPairHandler,
) -> None:
    """Delivery is at-least-once, so redelivery must stay harmless."""
    await catalog.add(make_qa_pair("q-1", events_collection))
    command = make_command()

    await upsert_qa_pair_handler.handle(command)
    await upsert_qa_pair_handler.handle(command)

    assert [document.external_id for document in index_writer.upserted] == [
        ExternalId(value="q-1"),
        ExternalId(value="q-1"),
    ]
    assert index_writer.upserted[0] == index_writer.upserted[1]
