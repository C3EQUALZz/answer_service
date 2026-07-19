from answer_service.application.commands.search.remove_qa_pair.command import (
    RemoveQAPairCommand,
)
from answer_service.application.commands.search.remove_qa_pair.handler import (
    RemoveQAPairHandler,
)
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from tests.unit.stubs.infrastructure import RecordingSearchIndexWriter


async def test_removal_deletes_from_the_index(
    index_writer: RecordingSearchIndexWriter,
    remove_qa_pair_handler: RemoveQAPairHandler,
) -> None:
    await remove_qa_pair_handler.handle(
        RemoveQAPairCommand(external_id=ExternalId(value="q-gone")),
    )

    assert index_writer.deleted == [ExternalId(value="q-gone")]
    assert index_writer.upserted == []


async def test_removing_twice_is_harmless(
    index_writer: RecordingSearchIndexWriter,
    remove_qa_pair_handler: RemoveQAPairHandler,
) -> None:
    """Delivery is at-least-once, so redelivery must stay harmless."""
    command = RemoveQAPairCommand(external_id=ExternalId(value="q-gone"))

    await remove_qa_pair_handler.handle(command)
    await remove_qa_pair_handler.handle(command)

    assert index_writer.deleted == [
        ExternalId(value="q-gone"),
        ExternalId(value="q-gone"),
    ]
