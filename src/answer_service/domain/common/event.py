from dataclasses import dataclass, field
from datetime import datetime

from .event_id import EventId


@dataclass(frozen=True, kw_only=True)
class Event:
    event_id: EventId | None = field(default=None, init=False)
    event_date: datetime | None = field(default=None, init=False)

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    def set_event_id(self, event_id: EventId) -> None:
        if self.event_id:
            return

        object.__setattr__(self, "event_id", event_id)  # ruff:ignore[unnecessary-dunder-call]

    def set_event_date(self, event_date: datetime) -> None:
        if self.event_date:
            return

        object.__setattr__(self, "event_date", event_date)  # ruff:ignore[unnecessary-dunder-call]
