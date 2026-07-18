"""Signatures of the arrangement fixtures.

Kept beside them rather than inside ``conftest.py`` so a test can name the type
it depends on without importing a conftest, which pytest owns.
"""

from collections.abc import Awaitable, Callable
from typing import Protocol

from httpx import Response

from answer_service.application.common.mediator.markers import BaseRequest
from answer_service.application.common.ports.outbox import OutboxMessage
from answer_service.domain.indexing.entities.indexing_task import IndexingTask
from answer_service.domain.indexing.entities.qa_pair import QAPair
from answer_service.domain.indexing.value_objects.task_id import TaskId

type OutboxSeeder = Callable[[int], Awaitable[list[OutboxMessage]]]
type TaskStorer = Callable[[IndexingTask], Awaitable[TaskId]]
type PairStorer = Callable[..., Awaitable[None]]
type PairBuilder = Callable[..., QAPair]
type QueryLogStorer = Callable[..., Awaitable[None]]
type SourceFileUploader = Callable[..., Awaitable[Response]]


class CommandSender(Protocol):
    """Dispatches one command through the mediator, in a scope of its own."""

    async def __call__[TResponse](self, command: BaseRequest[TResponse]) -> TResponse: ...
