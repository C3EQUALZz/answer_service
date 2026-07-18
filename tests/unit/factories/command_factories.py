"""Builders for the command DTOs the handlers are dispatched with."""

from answer_service.application.commands.indexing.enqueue_indexing.command import (
    EnqueueIndexingCommand,
)

CSV_HEADER = b"external_id,question,answer,category,updated_at\n"


def make_enqueue_indexing_command(
    content: bytes = CSV_HEADER,
    filename: str = "faq.csv",
    content_type: str | None = "text/csv",
) -> EnqueueIndexingCommand:
    return EnqueueIndexingCommand(
        content=content,
        filename=filename,
        content_type=content_type,
    )
