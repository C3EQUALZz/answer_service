import logging
from typing import Final, override

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from answer_service.application.common.ports.gateways import (
    QACatalogCommandGateway,
    QACatalogQueryGateway,
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
        self._session.add(pair)

    @override
    async def read_by_id(self, external_id: ExternalId) -> QAPair | None:
        stmt = select(QAPair).where(qa_pairs_table.c.external_id == external_id)
        try:
            pair = (await self._session.execute(stmt)).scalar_one_or_none()
        except SQLAlchemyError as e:
            msg = "Failed to read the QA pair."
            raise RepoError(msg) from e
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
            msg = "Failed to delete the QA pair."
            raise RepoError(msg) from e

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

    def _inject(self, pair: QAPair) -> QAPair:
        pair.events_collection = self._events_collection
        return pair
