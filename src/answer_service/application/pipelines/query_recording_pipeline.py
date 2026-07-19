import logging
import time
from typing import Any, Final, override

from answer_service.application.common.analytics import RecordableQuery, ServedQuery
from answer_service.application.common.mediator.handlers import (
    HandleNext,
    PipelineHandler,
)
from answer_service.application.common.ports.gateways import AnalyticsCommandGateway
from answer_service.application.common.ports.transaction_manager import (
    TransactionManager,
)
from answer_service.domain.analytics.factories.query_log_factory import QueryLogFactory
from answer_service.domain.analytics.value_objects.category_label import CategoryLabel
from answer_service.domain.analytics.value_objects.error_code import ErrorCode
from answer_service.domain.analytics.value_objects.latency import Latency
from answer_service.domain.analytics.value_objects.query_execution import QueryExecution
from answer_service.domain.analytics.value_objects.query_outcome import QueryOutcome
from answer_service.domain.analytics.value_objects.query_text import QueryText
from answer_service.domain.common.error import AppError

logger: Final[logging.Logger] = logging.getLogger(__name__)

MILLISECONDS_PER_SECOND: Final[int] = 1000


class QueryRecordingPipeline[TQuery: RecordableQuery[Any], TResponse: ServedQuery](
    PipelineHandler[TQuery, TResponse],
):
    """Writes every served query to the journal the reports are built from.

    A pipeline rather than a call at each route, because the statistics only
    mean anything if nothing escapes them: an endpoint that forgets to record
    does not fail, it quietly under-reports, and the gap report goes on looking
    healthy while questions the catalog cannot answer pile up unseen.

    It measures the latency itself, around the handler, so the number in the
    report is time spent answering rather than time spent in HTTP.

    Recording commits on its own. Queries run outside the transaction pipeline —
    they mutate nothing — so this is the only writer in the request and owns its
    boundary.
    """

    def __init__(
        self,
        query_log_factory: QueryLogFactory,
        analytics_gateway: AnalyticsCommandGateway,
        transaction_manager: TransactionManager,
    ) -> None:
        self._query_log_factory: Final[QueryLogFactory] = query_log_factory
        self._analytics_gateway: Final[AnalyticsCommandGateway] = analytics_gateway
        self._transaction_manager: Final[TransactionManager] = transaction_manager

    @override
    async def handle(
        self,
        request: TQuery,
        handle_next: HandleNext[TQuery, TResponse],
    ) -> TResponse:
        started_at = time.perf_counter()
        try:
            response = await handle_next(request)
        except AppError as error:
            await self._record_failure(
                request,
                error,
                self._elapsed_ms(started_at),
            )
            raise

        elapsed_ms = self._elapsed_ms(started_at)
        logger.info(
            "query_recording: %s served in %d ms",
            type(request).__name__,
            elapsed_ms,
        )

        await self._record(request, response, elapsed_ms)
        return response

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return round((time.perf_counter() - started_at) * MILLISECONDS_PER_SECOND)

    async def _record(
        self,
        request: TQuery,
        response: TResponse,
        latency_ms: int,
    ) -> None:
        """Logs one served query, and never fails the request it describes.

        The caller already has their results by the time this runs; losing a
        reporting row is a smaller harm than turning a success into a 500. The
        failure is logged at exception level so the report going quiet is still
        noticed.
        """
        await self._write(
            request,
            outcome=QueryOutcome(
                results_count=response.results_count,
                top_score=response.top_score,
            ),
            execution=QueryExecution.succeeded(),
            latency_ms=latency_ms,
        )

    async def _record_failure(
        self,
        request: TQuery,
        error: AppError,
        latency_ms: int,
    ) -> None:
        """Logs a query that raised, then lets the caller re-raise it.

        Recorded with no results rather than left out: a request the service
        could not serve still happened, and a report that counted only the
        successes would show an outage as a drop in traffic.

        The error's type is the code. It is stable across releases and carries
        no identifier, unlike the message, which would split one recurring
        fault into a row per occurrence.
        """
        await self._write(
            request,
            outcome=QueryOutcome(results_count=0),
            execution=QueryExecution.failed(ErrorCode(value=type(error).__name__)),
            latency_ms=latency_ms,
        )

    async def _write(
        self,
        request: TQuery,
        *,
        outcome: QueryOutcome,
        execution: QueryExecution,
        latency_ms: int,
    ) -> None:
        try:
            query_log = self._query_log_factory.create(
                text=QueryText(content=request.journalled_text),
                kind=request.journalled_kind,
                outcome=outcome,
                latency=Latency(milliseconds=latency_ms),
                execution=execution,
                category=(
                    CategoryLabel(value=request.journalled_category)
                    if request.journalled_category is not None
                    else None
                ),
            )
            await self._analytics_gateway.add(query_log)
            await self._transaction_manager.commit()
            logger.info(
                "query_recording: journalled %s query '%s' (%s, %d result(s), %d ms)",
                request.journalled_kind.value,
                request.journalled_text,
                execution.status.value,
                outcome.results_count,
                latency_ms,
            )
        except AppError:
            logger.exception(
                "failed to record a %s query for reporting",
                request.journalled_kind.value,
            )
            await self._transaction_manager.rollback()
