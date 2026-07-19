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
    QueryLogEntry,
    QueryLogFilters,
    QueryStatistics,
)
from answer_service.application.common.query_params.sorting import SortingOrder
from answer_service.infrastructure.errors import RepoError
from answer_service.infrastructure.mappers.query_log_entry_mapper import (
    QueryLogEntryMapper,
)
from answer_service.infrastructure.persistence.models import query_logs_table

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from answer_service.application.common.query_params.pagination import Pagination
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

    def __init__(
        self,
        session: AsyncSession,
        entry_mapper: QueryLogEntryMapper,
    ) -> None:
        self._session: Final[AsyncSession] = session
        self._entry_mapper: Final[QueryLogEntryMapper] = entry_mapper

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
            logger.exception("failed to read query statistics")
            msg = "Failed to read query statistics."
            raise RepoError(msg) from e

        return QueryStatistics(
            total=row.total,
            unanswered=row.unanswered,
            average_latency_ms=float(row.average_latency or 0.0),
        )

    @override
    async def read_unanswered_queries(
        self,
        period: Period,
        pagination: Pagination,
        sorting_order: SortingOrder,
    ) -> Sequence[QueryFrequency]:
        return await self._read_frequencies(
            self._frequency_stmt(period, pagination, sorting_order).where(
                query_logs_table.c.results_count == UNANSWERED,
            ),
            "Failed to read unanswered queries.",
        )

    @override
    async def read_popular_queries(
        self,
        period: Period,
        pagination: Pagination,
        sorting_order: SortingOrder,
    ) -> Sequence[QueryFrequency]:
        return await self._read_frequencies(
            self._frequency_stmt(period, pagination, sorting_order),
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

        return [
            QueryFrequency(text=row.text.content, occurrences=row.occurrences)
            for row in rows
        ]

    @override
    async def read_query_logs(
        self,
        filters: QueryLogFilters,
        pagination: Pagination,
        sorting_order: SortingOrder,
    ) -> Sequence[QueryLogEntry]:
        occurred_at = query_logs_table.c.occurred_at
        ordering = (
            occurred_at.asc() if sorting_order is SortingOrder.ASC else occurred_at.desc()
        )
        stmt = (
            select(query_logs_table)
            .where(self._matching(filters))
            # The id breaks ties, so a page boundary cannot fall in the middle
            # of a group of rows the database is free to reorder.
            .order_by(ordering, query_logs_table.c.id.asc())
            .limit(pagination.limit)
            .offset(pagination.offset)
        )

        try:
            rows = (await self._session.execute(stmt)).all()
        except SQLAlchemyError as e:
            logger.exception("failed to read the query journal")
            msg = "Failed to read the query journal."
            raise RepoError(msg) from e

        return [self._entry_mapper.to_entry(row) for row in rows]

    @override
    async def count_query_logs(self, filters: QueryLogFilters) -> int:
        stmt = (
            select(func.count())
            .select_from(query_logs_table)
            .where(
                self._matching(filters),
            )
        )

        try:
            total = (await self._session.execute(stmt)).scalar_one()
        except SQLAlchemyError as e:
            logger.exception("failed to count the query journal")
            msg = "Failed to count the query journal."
            raise RepoError(msg) from e

        return int(total)

    @staticmethod
    def _matching(filters: QueryLogFilters) -> ColumnElement[bool]:
        """Every filter the listing supports, ANDed into one predicate.

        Shared by the page and its count so the two can never disagree about
        what is being listed.
        """
        predicates: list[ColumnElement[bool]] = [
            SqlAlchemyAnalyticsGateway._within(filters.period),
        ]
        if filters.kind is not None:
            predicates.append(query_logs_table.c.kind == filters.kind)
        if filters.status is not None:
            predicates.append(query_logs_table.c.status == filters.status)
        return and_(*predicates)

    @staticmethod
    def _frequency_stmt(
        period: Period,
        pagination: Pagination,
        sorting_order: SortingOrder,
    ) -> Select[tuple[object, int]]:
        occurrences = func.count().label("occurrences")
        ordering = (
            occurrences.asc() if sorting_order is SortingOrder.ASC else occurrences.desc()
        )
        return (
            select(query_logs_table.c.text, occurrences)
            .where(SqlAlchemyAnalyticsGateway._within(period))
            .group_by(query_logs_table.c.text)
            .order_by(ordering, query_logs_table.c.text.asc())
            .limit(pagination.limit)
            .offset(pagination.offset)
        )

    @staticmethod
    def _within(period: Period) -> ColumnElement[bool]:
        """Half-open window, so consecutive periods never double-count a row."""
        return and_(
            query_logs_table.c.occurred_at >= period.start,
            query_logs_table.c.occurred_at < period.end,
        )
