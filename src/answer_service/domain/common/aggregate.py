from collections.abc import Hashable
from dataclasses import dataclass

from .entity import Entity
from .events_collection import EventsCollection


@dataclass(eq=False, kw_only=True)
class Aggregate[EntityId: Hashable](Entity[EntityId]):
    events_collection: EventsCollection
