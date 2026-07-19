import logging
from collections.abc import Iterable
from typing import Final, override

from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from answer_service.application.common.ports.gateways import (
    CatalogStatistics,
    QACatalogCommandGateway,
    QACatalogQueryGateway,
    QAPairView,
)
from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.entities.qa_pair import QAPair
from answer_service.domain.indexing.value_objects.content_hash import ContentHash
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.infrastructure.errors import RepoError
from answer_service.infrastructure.persistence.models import qa_pairs_table

logger: Final[logging.Logger] = logging.getLogger(__name__)


class SqlAlchemyQACatalogGateway(QACatalogCommandGateway, QACatalogQueryGateway):
    """Both sides of the QA catalog over one session.

    Aggregates loaded by the ORM are constructed without ``__init__``, so their
    ``events_collection`` is missing. Every read injects the request-scoped one
    before handing the aggregate out — otherwise a mutation would raise instead
    of recording its event.
    """

    def __init__(
        self,
        session: AsyncSession,
        events_collection: EventsCollection,
    ) -> None:
        self._session: Final[AsyncSession] = session
        self._events_collection: Final[EventsCollection] = events_collection

    @override
    async def add(self, pair: QAPair) -> None:
        logger.debug("qa_catalog: staging '%s' for insert", pair.id)
        self._session.add(pair)

    @override
    async def read_by_id(self, external_id: ExternalId) -> QAPair | None:
        stmt = select(QAPair).where(qa_pairs_table.c.external_id == external_id)
        try:
            pair = (await self._session.execute(stmt)).scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.exception("qa_catalog: failed to read '%s'", external_id)
            msg = "Failed to read the QA pair."
            raise RepoError(msg) from e

        logger.debug(
            "qa_catalog: '%s' %s",
            external_id,
            "found" if pair is not None else "not found",
        )
        return self._inject(pair) if pair is not None else None

    @override
    async def update(self, pair: QAPair) -> None:
        """No-op by design: the pair is already tracked by the session.

        ``read_by_id`` returns the identity-mapped instance, so the mutation the
        handler made is flushed with the transaction. The method exists so the
        application states its intent to write.
        """

    @override
    async def delete_by_id(self, external_id: ExternalId) -> None:
        stmt = delete(qa_pairs_table).where(
            qa_pairs_table.c.external_id == external_id,
        )
        try:
            await self._session.execute(stmt)
        except SQLAlchemyError as e:
            logger.exception("qa_catalog: failed to delete '%s'", external_id)
            msg = "Failed to delete the QA pair."
            raise RepoError(msg) from e

        logger.debug("qa_catalog: deleted '%s'", external_id)

    @override
    async def read_fingerprints(self) -> dict[ExternalId, ContentHash]:
        """Reads the whole manifest as columns, not aggregates.

        The sync diff needs one hash per pair; loading full aggregates to throw
        them away would cost a catalog-sized instantiation on every run.
        """
        stmt = select(
            qa_pairs_table.c.external_id,
            qa_pairs_table.c.question,
            qa_pairs_table.c.answer,
            qa_pairs_table.c.category,
        )
        try:
            rows = (await self._session.execute(stmt)).all()
        except SQLAlchemyError as e:
            logger.exception("failed to read the catalog fingerprints")
            msg = "Failed to read the catalog fingerprints."
            raise RepoError(msg) from e

        return {
            row.external_id: ContentHash.of(
                question=row.question,
                answer=row.answer,
                category=row.category,
            )
            for row in rows
        }

    @override
    async def read_views(
        self,
        external_ids: Iterable[ExternalId],
    ) -> dict[ExternalId, QAPairView]:
        """Reads the ranked pairs as columns, in one round trip.

        Ranking hands over a handful of ids out of a whole catalog, so this is
        deliberately a narrow ``IN`` rather than a join against the ranking:
        the ordering already exists in memory and the database has no business
        recomputing it.
        """
        ids = list(external_ids)
        if not ids:
            return {}

        stmt = select(
            qa_pairs_table.c.external_id,
            qa_pairs_table.c.question,
            qa_pairs_table.c.answer,
            qa_pairs_table.c.category,
        ).where(qa_pairs_table.c.external_id.in_(ids))

        try:
            rows = (await self._session.execute(stmt)).all()
        except SQLAlchemyError as e:
            logger.exception("failed to read the ranked qa pairs")
            msg = "Failed to read the ranked QA pairs."
            raise RepoError(msg) from e

        return {
            row.external_id: QAPairView(
                external_id=row.external_id.value,
                question=row.question.content,
                answer=row.answer.content,
                category=row.category.value,
            )
            for row in rows
        }

    @override
    async def read_statistics(self) -> CatalogStatistics:
        """Counts in the database, not by loading the catalog."""
        total_stmt = select(func.count()).select_from(qa_pairs_table)
        per_category_stmt = select(
            qa_pairs_table.c.category,
            func.count().label("pairs"),
        ).group_by(qa_pairs_table.c.category)

        try:
            total = (await self._session.execute(total_stmt)).scalar_one()
            rows = (await self._session.execute(per_category_stmt)).all()
        except SQLAlchemyError as e:
            logger.exception("failed to read the catalog statistics")
            msg = "Failed to read the catalog statistics."
            raise RepoError(msg) from e

        return CatalogStatistics(
            total_pairs=total,
            pairs_per_category={row.category.value: row.pairs for row in rows},
        )

    def _inject(self, pair: QAPair) -> QAPair:
        pair.events_collection = self._events_collection
        return pair
