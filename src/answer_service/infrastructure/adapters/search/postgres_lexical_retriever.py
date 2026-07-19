import logging
from typing import TYPE_CHECKING, Final, final, override

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import Function

from answer_service.application.common.ports.search import LexicalRetriever
from answer_service.domain.indexing.value_objects.category import Category
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.search.value_objects.score import Score
from answer_service.domain.search.value_objects.scored_candidate import ScoredCandidate
from answer_service.infrastructure.errors import RepoError
from answer_service.infrastructure.persistence.models.qa_pair import (
    TEXT_SEARCH_CONFIG,
    qa_pairs_table,
)
from answer_service.setup.configs.search_config import SearchConfig

if TYPE_CHECKING:
    from collections.abc import Sequence

    from answer_service.domain.search.value_objects.search_criteria import SearchCriteria

logger: Final[logging.Logger] = logging.getLogger(__name__)

RANK_LABEL: Final[str] = "rank"


@final
class PostgresLexicalRetriever(LexicalRetriever):
    """Keyword retrieval over the ``qa_pairs`` full-text index.

    Runs against the same rows the catalog serves, so a pair is lexically
    findable the moment it is committed — there is no second store to fall
    behind. That is the opposite trade-off from the dense side, which only sees
    a pair once the outbox has been relayed.
    """

    def __init__(self, session: AsyncSession, search_config: SearchConfig) -> None:
        self._session: Final[AsyncSession] = session
        self._score_floor: Final[float] = search_config.lexical_score_floor

    @override
    async def retrieve(self, criteria: SearchCriteria) -> Sequence[ScoredCandidate]:
        logger.debug(
            "postgres_lexical: searching '%s', top_k=%d, floor=%.3f, category=%s",
            criteria.query.content,
            criteria.top_k.value,
            self._score_floor,
            criteria.category,
        )

        try:
            statement = self._statement(criteria, self._score_floor)
            rows = (await self._session.execute(statement)).all()
        except SQLAlchemyError as e:
            logger.exception("postgres_lexical: search failed")
            msg = "Failed to query PostgreSQL for lexical candidates."
            raise RepoError(msg) from e

        logger.info(
            "postgres_lexical: %d candidate(s) above floor %.3f",
            len(rows),
            self._score_floor,
        )
        for row in rows:
            logger.debug(
                "postgres_lexical: '%s' ranked %.4f",
                row.external_id,
                float(getattr(row, RANK_LABEL)),
            )

        return [
            ScoredCandidate(
                external_id=row.external_id,
                score=Score(value=float(getattr(row, RANK_LABEL))),
            )
            for row in rows
        ]

    @staticmethod
    def _tsquery(text: str) -> Function[str]:
        """Turns what a user typed into a tsquery matching *any* of its terms.

        Normalising through ``to_tsvector`` first is what makes arbitrary input
        safe: stemming and stopword removal happen there, and punctuation that
        would be a syntax error to ``to_tsquery`` never reaches it. A query with
        nothing left after that — blank, or only stopwords — becomes an empty
        tsquery, which matches nothing instead of raising.

        The terms are OR-ed rather than AND-ed on purpose. The parsers that
        accept free text all AND, and a question phrased as a sentence then
        matches only pairs containing every one of its words, which in practice
        is none: this retriever contributed nothing at all to natural-language
        queries until it OR-ed. Recall is its job here — ``ts_rank_cd`` still
        orders by how well a pair covers the query, and fusion supplies the
        precision.
        """
        lexemes = func.tsvector_to_array(func.to_tsvector(TEXT_SEARCH_CONFIG, text))
        return func.to_tsquery(
            TEXT_SEARCH_CONFIG,
            func.array_to_string(lexemes, " | "),
        )

    @classmethod
    def _statement(
        cls,
        criteria: SearchCriteria,
        score_floor: float,
    ) -> Select[tuple[ExternalId, float]]:
        """Ranks matches with ``ts_rank_cd`` and drops the ones that rank too low.

        Cover density ranking rewards matched terms appearing close together,
        which is what distinguishes a pair that is *about* the query from one
        that merely mentions one of its words. OR-ing the terms means a pair
        sharing a single incidental word matches at all, so the floor is what
        stops that from counting as an answer.
        """
        query = cls._tsquery(criteria.query.content)
        rank = func.ts_rank_cd(qa_pairs_table.c.search_vector, query).label(RANK_LABEL)

        statement = (
            select(qa_pairs_table.c.external_id, rank)
            .where(qa_pairs_table.c.search_vector.op("@@")(query))
            .where(rank >= score_floor)
            .order_by(rank.desc(), qa_pairs_table.c.external_id)
            .limit(criteria.top_k.value)
        )

        if criteria.category is not None:
            statement = statement.where(
                qa_pairs_table.c.category == Category(value=criteria.category.value),
            )

        return statement
