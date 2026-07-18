import json

from answer_service.domain.indexing.events import IndexingCompleted, QAPairAdded
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.sync_stats import SyncStats
from answer_service.infrastructure.adapters.common import RetortEventSerializer
from tests.unit.factories.domain_factories import make_task_id


def test_the_event_type_is_carried_as_its_class_name(
    serializer: RetortEventSerializer,
) -> None:
    """The projector routes on this string; nothing else identifies the event."""
    message = serializer.serialize(QAPairAdded(external_id=ExternalId(value="q-1")))

    assert message.event_type == "QAPairAdded"


def test_the_payload_is_json_the_projector_can_read(
    serializer: RetortEventSerializer,
) -> None:
    message = serializer.serialize(QAPairAdded(external_id=ExternalId(value="q-1")))

    payload = json.loads(message.payload)
    assert payload["external_id"] == {"value": "q-1"}


def test_value_objects_and_stats_survive_serialization(
    serializer: RetortEventSerializer,
) -> None:
    message = serializer.serialize(
        IndexingCompleted(
            task_id=make_task_id(),
            stats=SyncStats(created=1, updated=2, deleted=3, skipped=4),
        ),
    )

    payload = json.loads(message.payload)
    assert payload["task_id"] == str(make_task_id())
    assert payload["stats"] == {
        "created": 1,
        "updated": 2,
        "deleted": 3,
        "skipped": 4,
    }


def test_every_message_gets_its_own_row_id(serializer: RetortEventSerializer) -> None:
    """The outbox row id is the idempotency key consumers deduplicate on."""
    event = QAPairAdded(external_id=ExternalId(value="q-1"))

    first = serializer.serialize(event)
    second = serializer.serialize(event)

    assert first.id != second.id


def test_an_event_is_stamped_once_and_keeps_its_identity(
    serializer: RetortEventSerializer,
) -> None:
    """A redelivered event must not change the id it is deduplicated by."""
    event = QAPairAdded(external_id=ExternalId(value="q-1"))

    first = json.loads(serializer.serialize(event).payload)
    second = json.loads(serializer.serialize(event).payload)

    assert first["event_id"] == second["event_id"]
    assert first["event_date"] == second["event_date"]
