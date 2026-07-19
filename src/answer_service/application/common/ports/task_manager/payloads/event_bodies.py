from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EventBody(BaseModel):
    """Pydantic mirror of a serialized domain event.

    The outbox stores events as JSON dumped by adaptix, which renders the two
    kinds of value object differently: a dataclass one becomes an object, a
    ``NewType`` over ``UUID`` becomes a bare string. Subclasses declare the
    shape their task needs and let pydantic reject the rest, so no task reaches
    into raw JSON by hand.

    Unknown fields are ignored rather than rejected: an event gains fields over
    time, and a consumer that only reads one of them has no business failing
    because another appeared.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)


class RawEventBody(EventBody):
    """Body carried through without being interpreted.

    Used by the publisher, which forwards what the outbox stored without
    knowing which task will read it. Extras are kept so the typed body on the
    consuming side still finds its fields.
    """

    model_config = ConfigDict(extra="allow", frozen=True)


class ExternalIdBody(EventBody):
    """``ExternalId`` is a dataclass value object, so it is dumped as an object."""

    value: str


class QAPairEventBody(EventBody):
    """Body shared by the catalog events the search projection reacts to."""

    external_id: ExternalIdBody


class IndexingTaskQueuedBody(EventBody):
    """``TaskId`` is a ``NewType`` over ``UUID``, so it is dumped bare."""

    task_id: UUID
