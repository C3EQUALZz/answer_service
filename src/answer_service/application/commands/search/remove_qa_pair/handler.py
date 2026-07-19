import logging
from typing import Final, override

from answer_service.application.commands.search.remove_qa_pair.command import (
    RemoveQAPairCommand,
)
from answer_service.application.common.mediator.handlers import CommandHandler
from answer_service.application.common.ports.search import SearchIndexWriter

logger: Final[logging.Logger] = logging.getLogger(__name__)


class RemoveQAPairHandler(CommandHandler[RemoveQAPairCommand, None]):
    """Clears a QA pair from the search index.

    Deleting an entry that is not there is not an error, so this is safe to
    replay — which it will be, because the relay delivers at least once.
    """

    def __init__(self, index_writer: SearchIndexWriter) -> None:
        self._index_writer: Final[SearchIndexWriter] = index_writer

    @override
    async def handle(self, command: RemoveQAPairCommand) -> None:
        logger.info("remove_qa_pair: dropping '%s' from the index", command.external_id)
        await self._index_writer.delete([command.external_id])
        logger.info("remove_qa_pair: '%s' is gone from the index", command.external_id)
