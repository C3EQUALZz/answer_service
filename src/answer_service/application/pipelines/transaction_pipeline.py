from typing import Any, Final, override

from answer_service.application.common.mediator.handlers import (
    HandleNext,
    PipelineHandler,
)
from answer_service.application.common.mediator.markers import Command
from answer_service.application.common.ports.transaction_manager import (
    TransactionManager,
)


class TransactionPipeline[TCommand: Command[Any], TResponse](
    PipelineHandler[TCommand, TResponse],
):
    """Wraps command handling in a unit-of-work boundary.

    Commits when the handler succeeds, rolls back and re-raises on any error.
    Applied to commands only — queries do not mutate state.
    """

    def __init__(self, transaction_manager: TransactionManager) -> None:
        self._transaction_manager: Final[TransactionManager] = transaction_manager

    @override
    async def handle(
        self,
        request: TCommand,
        handle_next: HandleNext[TCommand, TResponse],
    ) -> TResponse:
        try:
            response = await handle_next(request)
        except Exception:
            await self._transaction_manager.rollback()
            raise

        await self._transaction_manager.commit()
        return response
