from typing import TYPE_CHECKING

from answer_service.domain.common.service import BaseDomainService
from answer_service.domain.indexing.errors import DuplicateExternalIdError
from answer_service.domain.indexing.value_objects.sync_plan import SyncPlan

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from answer_service.domain.indexing.value_objects.content_hash import ContentHash
    from answer_service.domain.indexing.value_objects.desired_pair import DesiredPair
    from answer_service.domain.indexing.value_objects.external_id import ExternalId


class SyncPlanner(BaseDomainService):
    """Diffs the desired source pairs against the currently indexed fingerprints.

    Idempotent: a pair whose fingerprint matches the catalog is *skipped*, so
    re-running an unchanged file produces only skips. A pair present in the
    catalog but absent from the source is *deleted*.
    """

    def plan(
        self,
        *,
        desired: Sequence[DesiredPair],
        current: Mapping[ExternalId, ContentHash],
    ) -> SyncPlan:
        to_create: list[DesiredPair] = []
        to_update: list[DesiredPair] = []
        skipped: list[ExternalId] = []
        seen: set[ExternalId] = set()

        for pair in desired:
            if pair.external_id in seen:
                msg = f"Duplicate external_id in source: '{pair.external_id}'."
                raise DuplicateExternalIdError(msg)
            seen.add(pair.external_id)

            indexed_fingerprint = current.get(pair.external_id)
            if indexed_fingerprint is None:
                to_create.append(pair)
            elif indexed_fingerprint != pair.fingerprint:
                to_update.append(pair)
            else:
                skipped.append(pair.external_id)

        to_delete = [external_id for external_id in current if external_id not in seen]

        return SyncPlan(
            to_create=tuple(to_create),
            to_update=tuple(to_update),
            to_delete=tuple(to_delete),
            skipped=tuple(skipped),
        )
