from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self, final

from answer_service.domain.common.aggregate import Aggregate
from answer_service.domain.indexing.events import (
    QAPairAdded,
    QAPairContentUpdated,
    QAPairRemoved,
)
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.qa_content import QAContent

if TYPE_CHECKING:
    from answer_service.domain.common.events_collection import EventsCollection
    from answer_service.domain.indexing.value_objects.content_hash import ContentHash


@final
@dataclass(eq=False, kw_only=True)
class QAPair(Aggregate[ExternalId]):
    """A question-answer record — the unit synced and indexed for search.

    Identity is the source-provided ``ExternalId``. Content lives in a single
    :class:`QAContent` value object, so change detection is a value comparison
    and synchronization stays idempotent: re-applying identical content is a
    no-op.
    """

    content: QAContent
    source_updated_at: datetime

    @classmethod
    def register(
        cls,
        *,
        external_id: ExternalId,
        content: QAContent,
        source_updated_at: datetime,
        events_collection: EventsCollection,
    ) -> Self:
        pair = cls(
            id=external_id,
            content=content,
            source_updated_at=source_updated_at,
            events_collection=events_collection,
        )
        pair.events_collection.add_event(QAPairAdded(external_id=external_id))
        return pair

    def matches(self, content_hash: ContentHash) -> bool:
        """Whether the pair's current content equals the given fingerprint."""
        return self.content.fingerprint == content_hash

    def update_content(
        self,
        *,
        content: QAContent,
        source_updated_at: datetime,
    ) -> bool:
        """Apply new content; returns ``True`` only if something changed.

        Idempotent: identical content leaves the pair untouched and emits no
        event.
        """
        if content == self.content:
            return False

        self.content = content
        self.source_updated_at = source_updated_at
        self.updated_at = datetime.now(UTC)
        self.events_collection.add_event(QAPairContentUpdated(external_id=self.id))
        return True

    def mark_removed(self) -> None:
        """Signal the pair is gone from the source and must leave the index."""
        self.events_collection.add_event(QAPairRemoved(external_id=self.id))
