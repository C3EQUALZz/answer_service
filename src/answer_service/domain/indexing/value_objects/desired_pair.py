from dataclasses import dataclass
from datetime import datetime
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.indexing.value_objects.content_hash import ContentHash
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.qa_content import QAContent


@dataclass(frozen=True, kw_only=True)
class DesiredPair(ValueObject):
    """A QA pair as it appears in the source file — the desired end state.

    A lightweight descriptor (not the aggregate): the planner works over these
    to decide creates / updates / deletes without building aggregates for pairs
    that turn out unchanged.
    """

    external_id: ExternalId
    content: QAContent
    source_updated_at: datetime

    @property
    def fingerprint(self) -> ContentHash:
        return self.content.fingerprint

    @override
    def _validate(self) -> None:
        """Component value objects validate themselves."""
