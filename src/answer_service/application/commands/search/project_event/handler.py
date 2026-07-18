import json
import logging
from typing import Any, Final, override

from answer_service.application.commands.search.project_event.command import (
    ProjectEventCommand,
)
from answer_service.application.common.mediator.handlers import CommandHandler
from answer_service.application.common.ports.gateways import QACatalogCommandGateway
from answer_service.application.common.ports.search import (
    IndexDocument,
    SearchIndexWriter,
)
from answer_service.application.error import MalformedEventPayloadError
from answer_service.domain.indexing.entities.qa_pair import QAPair
from answer_service.domain.indexing.value_objects.external_id import ExternalId

logger: Final[logging.Logger] = logging.getLogger(__name__)

EXTERNAL_ID_KEY: Final[str] = "external_id"
VALUE_KEY: Final[str] = "value"

UPSERT_EVENTS: Final[frozenset[str]] = frozenset(
    {"QAPairAdded", "QAPairContentUpdated"},
)
DELETE_EVENTS: Final[frozenset[str]] = frozenset({"QAPairRemoved"})


class ProjectEventHandler(CommandHandler[ProjectEventCommand, None]):
    """Projects a catalog change onto the search index.

    Every outbox message reaches this handler, including the task-lifecycle
    events that have nothing to do with search; those are ignored rather than
    treated as errors, so adding a domain event never breaks the projector.

    Reads the pair's current state rather than trusting the event to carry it.
    That makes projection self-correcting: replaying an old event writes what
    the catalog says *now*, so a redelivery can never resurrect stale content.
    Combined with the point id being derived from the external id, applying the
    same event twice is indistinguishable from applying it once.
    """

    def __init__(
        self,
        catalog: QACatalogCommandGateway,
        index_writer: SearchIndexWriter,
    ) -> None:
        self._catalog: Final[QACatalogCommandGateway] = catalog
        self._index_writer: Final[SearchIndexWriter] = index_writer

    @override
    async def handle(self, command: ProjectEventCommand) -> None:
        if command.event_type in UPSERT_EVENTS:
            await self._upsert(self._external_id_of(command))
            return

        if command.event_type in DELETE_EVENTS:
            await self._index_writer.delete([self._external_id_of(command)])
            return

        logger.debug(
            "project_event: ignoring non-search event %s",
            command.event_type,
        )

    async def _upsert(self, external_id: ExternalId) -> None:
        pair = await self._catalog.read_by_id(external_id)
        if pair is None:
            # Deleted between the write and this projection; the removal event
            # is already in the outbox and will clear the index entry.
            logger.debug(
                "project_event: '%s' is gone from the catalog, skipping upsert",
                external_id,
            )
            return

        await self._index_writer.upsert([self._to_document(pair)])

    @staticmethod
    def _to_document(pair: QAPair) -> IndexDocument:
        return IndexDocument(
            external_id=pair.id,
            question=pair.content.question.content,
            answer=pair.content.answer.content,
            category=pair.content.category.value,
        )

    @staticmethod
    def _external_id_of(command: ProjectEventCommand) -> ExternalId:
        try:
            payload: dict[str, Any] = json.loads(command.payload)
            return ExternalId(value=payload[EXTERNAL_ID_KEY][VALUE_KEY])
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            msg = (
                f"Event '{command.event_type}' (message '{command.message_id}') "
                f"carries no readable external_id."
            )
            raise MalformedEventPayloadError(msg) from e
