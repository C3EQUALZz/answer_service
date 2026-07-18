from uuid import uuid4

import pytest

from answer_service.application.commands.search.project_event.command import (
    ProjectEventCommand,
)
from answer_service.application.commands.search.project_event.handler import (
    ProjectEventHandler,
)
from answer_service.application.error import MalformedEventPayloadError
from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from tests.unit.factories.domain_factories import make_qa_content, make_qa_pair
from tests.unit.factories.outbox_factories import make_event_payload
from tests.unit.stubs.gateways import InMemoryQACatalog
from tests.unit.stubs.infrastructure import RecordingSearchIndexWriter


def make_command(event_type: str, external_id: str = "q-1") -> ProjectEventCommand:
    return ProjectEventCommand(
        message_id=uuid4(),
        event_type=event_type,
        payload=make_event_payload(external_id),
    )


@pytest.mark.parametrize("event_type", ("QAPairAdded", "QAPairContentUpdated"))
async def test_indexes_the_current_catalog_content(
    event_type: str,
    catalog: InMemoryQACatalog,
    events_collection: EventsCollection,
    index_writer: RecordingSearchIndexWriter,
    project_event_handler: ProjectEventHandler,
) -> None:
    await catalog.add(
        make_qa_pair(
            "q-1",
            events_collection,
            make_qa_content(question="How?", answer="Like this.", category="howto"),
        ),
    )

    await project_event_handler.handle(make_command(event_type))

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
    project_event_handler: ProjectEventHandler,
) -> None:
    """A replayed old event must not resurrect stale content."""
    await catalog.add(
        make_qa_pair(
            "q-1",
            events_collection,
            make_qa_content(answer="The newest answer."),
        ),
    )

    await project_event_handler.handle(make_command("QAPairAdded"))

    assert index_writer.upserted[0].answer == "The newest answer."


async def test_removal_deletes_from_the_index(
    index_writer: RecordingSearchIndexWriter,
    project_event_handler: ProjectEventHandler,
) -> None:
    await project_event_handler.handle(make_command("QAPairRemoved", "q-gone"))

    assert index_writer.deleted == [ExternalId(value="q-gone")]
    assert index_writer.upserted == []


async def test_a_pair_deleted_before_projection_is_skipped(
    index_writer: RecordingSearchIndexWriter,
    project_event_handler: ProjectEventHandler,
) -> None:
    """The removal event is already queued and will clear the entry."""
    await project_event_handler.handle(make_command("QAPairAdded", "q-vanished"))

    assert index_writer.upserted == []
    assert index_writer.deleted == []


@pytest.mark.parametrize(
    "event_type",
    ("IndexingTaskQueued", "IndexingStarted", "IndexingCompleted", "IndexingFailed"),
)
async def test_non_search_events_are_ignored(
    event_type: str,
    index_writer: RecordingSearchIndexWriter,
    project_event_handler: ProjectEventHandler,
) -> None:
    """Every outbox message reaches the projector, not just the ones it wants."""
    await project_event_handler.handle(
        ProjectEventCommand(message_id=uuid4(), event_type=event_type, payload="{}"),
    )

    assert index_writer.upserted == []
    assert index_writer.deleted == []


async def test_replaying_an_event_is_indistinguishable_from_applying_it_once(
    catalog: InMemoryQACatalog,
    events_collection: EventsCollection,
    index_writer: RecordingSearchIndexWriter,
    project_event_handler: ProjectEventHandler,
) -> None:
    """Delivery is at-least-once, so redelivery must stay harmless."""
    await catalog.add(make_qa_pair("q-1", events_collection))
    command = make_command("QAPairAdded")

    await project_event_handler.handle(command)
    await project_event_handler.handle(command)

    assert [document.external_id for document in index_writer.upserted] == [
        ExternalId(value="q-1"),
        ExternalId(value="q-1"),
    ]
    assert index_writer.upserted[0] == index_writer.upserted[1]


async def test_an_unreadable_payload_is_rejected(
    project_event_handler: ProjectEventHandler,
) -> None:
    with pytest.raises(MalformedEventPayloadError):
        await project_event_handler.handle(
            ProjectEventCommand(
                message_id=uuid4(),
                event_type="QAPairAdded",
                payload="not json at all",
            ),
        )
