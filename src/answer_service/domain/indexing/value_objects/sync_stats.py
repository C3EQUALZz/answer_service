from dataclasses import dataclass
from typing import Self, override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.indexing.errors import NegativeSyncCountError


@dataclass(frozen=True, kw_only=True)
class SyncStats(ValueObject):
    """Outcome counters of a single synchronization run."""

    created: int
    updated: int
    deleted: int
    skipped: int

    @classmethod
    def empty(cls) -> Self:
        return cls(created=0, updated=0, deleted=0, skipped=0)

    @property
    def total(self) -> int:
        return self.created + self.updated + self.deleted + self.skipped

    @override
    def _validate(self) -> None:
        for name, count in (
            ("created", self.created),
            ("updated", self.updated),
            ("deleted", self.deleted),
            ("skipped", self.skipped),
        ):
            if count < 0:
                msg = f"{name} count must be >= 0, got {count}."
                raise NegativeSyncCountError(msg)
