import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Final, override

from sqlalchemy import Select, and_, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from answer_service.application.common.ports.gateways import (
    AnalyticsCommandGateway,
    AnalyticsQueryGateway,
    QueryFrequency,
    QueryStatistics,
)
from answer_service.infrastructure.errors import RepoError
from answer_service.infrastructure.persistence.models import query_logs_table

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from answer_service.domain.analytics.entities.query_log import QueryLog
    from answer_service.domain.analytics.value_objects.period import Period

logger: Final[logging.Logger] = logging.getLogger(__name__)

UNANSWERED: Final[int] = 0


class SqlAlchemyAnalyticsGateway(AnalyticsCommandGateway, AnalyticsQueryGateway):
    """Both sides of the query log over one session.

    Every read aggregates in the database. The log is the highest-volume table
    in the service — one row per request — so a report that pulled rows into
    Python would degrade in step with traffic, exactly when it matters most.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session: Final[AsyncSession] = session

    @override
    async def add(self, query_log: QueryLog) -> None:
        self._session.add(query_log)

    @override
    async def read_statistics(self, period: Period) -> QueryStatistics:
        stmt = select(
            func.count().label("total"),
            func
            .count()
            .filter(query_logs_table.c.results_count == UNANSWERED)
            .label("unanswered"),
            func.avg(query_logs_table.c.latency_ms).label("average_latency"),
        ).where(self._within(period))

        try:
            row = (await self._session.execute(stmt)).one()
        except SQLAlchemyError as e:
            msg = "Failed to read query statistics."
            raise RepoError(msg) from e

        return QueryStatistics(
            total=row.total,
            unanswered=row.unanswered,
            # AVG over no rows is NULL, and an idle period must report 0.0
            # rather than blow up the statistics page.
            average_latency_ms=float(row.average_latency or 0.0),
        )

    @override
    async def read_unanswered_queries(
        self,
        period: Period,
        limit: int,
    ) -> Sequence[QueryFrequency]:
        return await self._read_frequencies(
            self._frequency_stmt(period, limit).where(
                query_logs_table.c.results_count == UNANSWERED,
            ),
            "Failed to read unanswered queries.",
        )

    @override
    async def read_popular_queries(
        self,
        period: Period,
        limit: int,
    ) -> Sequence[QueryFrequency]:
        return await self._read_frequencies(
            self._frequency_stmt(period, limit),
            "Failed to read popular queries.",
        )

    async def _read_frequencies(
        self,
        stmt: Select[tuple[object, int]],
        error_message: str,
    ) -> Sequence[QueryFrequency]:
        try:
            rows = (await self._session.execute(stmt)).all()
        except SQLAlchemyError as e:
            raise RepoError(error_message) from e

        # The text column carries a value object type, so it comes back as
        # ``QueryText`` rather than a plain string.
        return [
            QueryFrequency(text=row.text.content, occurrences=row.occurrences)
            for row in rows
        ]

    @staticmethod
    def _frequency_stmt(period: Period, limit: int) -> Select[tuple[object, int]]:
        occurrences = func.count().label("occurrences")
        return (
            select(query_logs_table.c.text, occurrences)
            .where(SqlAlchemyAnalyticsGateway._within(period))
            .group_by(query_logs_table.c.text)
            .order_by(occurrences.desc())
            .limit(limit)
        )

    @staticmethod
    def _within(period: Period) -> ColumnElement[bool]:
        """Half-open window, so consecutive periods never double-count a row."""
        return and_(
            query_logs_table.c.occurred_at >= period.start,
            query_logs_table.c.occurred_at < period.end,
        )
