from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.indexing.value_objects.desired_pair import DesiredPair
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.sync_stats import SyncStats


@dataclass(frozen=True, kw_only=True)
class SyncPlan(ValueObject):
    """The categorised outcome of diffing the source file against the catalog.

    Pure data: the application applies it (writes to catalog + search stores)
    and records :meth:`stats` on the indexing task.
    """

    to_create: tuple[DesiredPair, ...]
    to_update: tuple[DesiredPair, ...]
    to_delete: tuple[ExternalId, ...]
    skipped: tuple[ExternalId, ...]

    def stats(self) -> SyncStats:
        return SyncStats(
            created=len(self.to_create),
            updated=len(self.to_update),
            deleted=len(self.to_delete),
            skipped=len(self.skipped),
        )

    @override
    def _validate(self) -> None:
        """Component value objects validate themselves."""
