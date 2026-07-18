from typing import Final, override

from answer_service.application.commands.analytics.record_query.command import (
    RecordQueryCommand,
)
from answer_service.application.common.mediator.handlers import CommandHandler
from answer_service.application.common.ports.gateways import AnalyticsCommandGateway
from answer_service.domain.analytics.factories.query_log_factory import QueryLogFactory
from answer_service.domain.analytics.value_objects.category_label import CategoryLabel
from answer_service.domain.analytics.value_objects.latency import Latency
from answer_service.domain.analytics.value_objects.query_outcome import QueryOutcome
from answer_service.domain.analytics.value_objects.query_text import QueryText


class RecordQueryHandler(CommandHandler[RecordQueryCommand, None]):
    """Turns a served request into a log entry.

    Runs in its own transaction, separate from the search that produced it:
    reporting must never be able to fail a request a user already got an answer
    to.
    """

    def __init__(
        self,
        query_log_factory: QueryLogFactory,
        analytics_gateway: AnalyticsCommandGateway,
    ) -> None:
        self._query_log_factory: Final[QueryLogFactory] = query_log_factory
        self._analytics_gateway: Final[AnalyticsCommandGateway] = analytics_gateway

    @override
    async def handle(self, command: RecordQueryCommand) -> None:
        query_log = self._query_log_factory.create(
            text=QueryText(content=command.text),
            kind=command.kind,
            outcome=QueryOutcome(
                results_count=command.results_count,
                top_score=command.top_score,
            ),
            latency=Latency(milliseconds=command.latency_ms),
            category=(
                CategoryLabel(value=command.category)
                if command.category is not None
                else None
            ),
        )
        await self._analytics_gateway.add(query_log)
