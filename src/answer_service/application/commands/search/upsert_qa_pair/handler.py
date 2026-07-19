import logging
from typing import Final, override

from answer_service.application.commands.search.upsert_qa_pair.command import (
    UpsertQAPairCommand,
)
from answer_service.application.common.mediator.handlers import CommandHandler
from answer_service.application.common.ports.gateways import QACatalogCommandGateway
from answer_service.application.common.ports.search import (
    IndexDocument,
    SearchIndexWriter,
)
from answer_service.domain.indexing.entities.qa_pair import QAPair

logger: Final[logging.Logger] = logging.getLogger(__name__)


class UpsertQAPairHandler(CommandHandler[UpsertQAPairCommand, None]):
    """Projects a QA pair's current state onto the search index.

    Reads the pair rather than trusting the event that triggered this to carry
    it. That makes projection self-correcting: replaying an old event writes
    what the catalog says *now*, so a redelivery can never resurrect stale
    content. Combined with the point id being derived from the external id,
    applying the same event twice is indistinguishable from applying it once.
    """

    def __init__(
        self,
        catalog: QACatalogCommandGateway,
        index_writer: SearchIndexWriter,
    ) -> None:
        self._catalog: Final[QACatalogCommandGateway] = catalog
        self._index_writer: Final[SearchIndexWriter] = index_writer

    @override
    async def handle(self, command: UpsertQAPairCommand) -> None:
        pair = await self._catalog.read_by_id(command.external_id)
        if pair is None:
            logger.debug(
                "upsert_qa_pair: '%s' is gone from the catalog, skipping",
                command.external_id,
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
