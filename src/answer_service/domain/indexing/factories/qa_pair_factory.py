import logging
from typing import TYPE_CHECKING, Final, final

from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.entities.qa_pair import QAPair

if TYPE_CHECKING:
    from datetime import datetime

    from answer_service.domain.indexing.value_objects.external_id import ExternalId
    from answer_service.domain.indexing.value_objects.qa_content import QAContent


logger: Final[logging.Logger] = logging.getLogger(__name__)


@final
class QAPairFactory:
    """Domain factory for the :class:`QAPair` aggregate.

    Receives the request-scoped ``EventsCollection`` via DI so every aggregate
    built within a request shares one collection and its events are published
    together.
    """

    def __init__(self, events_collection: EventsCollection) -> None:
        self._events_collection: Final[EventsCollection] = events_collection

    def create(
        self,
        *,
        external_id: ExternalId,
        content: QAContent,
        source_updated_at: datetime,
    ) -> QAPair:
        logger.debug("qa_pair_factory: registering '%s'", external_id)
        return QAPair.register(
            external_id=external_id,
            content=content,
            source_updated_at=source_updated_at,
            events_collection=self._events_collection,
        )
