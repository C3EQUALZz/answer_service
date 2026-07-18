from uuid import uuid4

from answer_service.domain.common.event import Event
from answer_service.domain.common.event_id import EventId
from tests.unit.factories.domain_factories import make_events_collection


class SampleEvent(Event):
    pass


def test_pulling_drains_the_collection() -> None:
    """The events pipeline pulls once; a second pull must find nothing."""
    collection = make_events_collection()
    collection.add_event(SampleEvent())

    first = list(collection.pull_events())
    second = list(collection.pull_events())

    assert len(first) == 1
    assert second == []


def test_events_are_pulled_in_the_order_they_happened() -> None:
    collection = make_events_collection()
    events = [SampleEvent() for _ in range(3)]
    for event in events:
        collection.add_event(event)

    assert list(collection.pull_events()) == events


def test_an_event_added_after_a_pull_belongs_to_the_next_batch() -> None:
    collection = make_events_collection()
    collection.add_event(SampleEvent())
    list(collection.pull_events())

    late = SampleEvent()
    collection.add_event(late)

    assert list(collection.pull_events()) == [late]


def test_removing_an_event_keeps_it_out_of_the_batch() -> None:
    collection = make_events_collection()
    kept, dropped = SampleEvent(), SampleEvent()
    collection.add_event(kept)
    collection.add_event(dropped)

    collection.remove_event(dropped)

    assert list(collection.pull_events()) == [kept]


def test_event_identity_is_stamped_only_once() -> None:
    """Re-serialising an event must not change the id consumers deduplicate on."""
    event = SampleEvent()
    event.set_event_id(EventId(uuid4()))
    first = event.event_id

    event.set_event_id(EventId(uuid4()))

    assert event.event_id == first


def test_event_type_is_the_class_name() -> None:
    assert SampleEvent().event_type == "SampleEvent"
