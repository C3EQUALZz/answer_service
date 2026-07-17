from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .event import Event

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(eq=False, frozen=True)
class EventsCollection:
    events: deque[Event]

    def add_event(self, event: Event) -> None:
        self.events.append(event)

    def remove_event(self, event: Event) -> None:
        self.events.remove(event)

    def pull_events(self) -> Iterable[Event]:
        copy_events: deque[Event] = self.events.copy()
        self.events.clear()
        return iter(copy_events)
