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
MATCHES_SUBQUERY: Final[str] = "matches"


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
        self._relative_floor: Final[float] = search_config.lexical_relative_floor
        self._absolute_floor: Final[float] = search_config.lexical_absolute_floor

    @override
    async def retrieve(self, criteria: SearchCriteria) -> Sequence[ScoredCandidate]:
        logger.debug(
            "postgres_lexical: searching '%s', top_k=%d, relative floor=%.2f, "
            "absolute floor=%.2f, category=%s",
            criteria.query.content,
            criteria.top_k.value,
            self._relative_floor,
            self._absolute_floor,
            criteria.category,
        )

        try:
            statement = self._statement(
                criteria,
                self._relative_floor,
                self._absolute_floor,
            )
            rows = (await self._session.execute(statement)).all()
        except SQLAlchemyError as e:
            logger.exception("postgres_lexical: search failed")
            msg = "Failed to query PostgreSQL for lexical candidates."
            raise RepoError(msg) from e

        logger.info(
            "postgres_lexical: %d candidate(s) within %.0f%% of the best match and "
            "above %.2f",
            len(rows),
            self._relative_floor * 100,
            self._absolute_floor,
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
        relative_floor: float,
        absolute_floor: float,
    ) -> Select[tuple[ExternalId, float]]:
        """Keeps the matches that rank near the best one and are good in themselves.

        Cover density ranking rewards matched terms appearing close together,
        which is what distinguishes a pair that is *about* the query from one
        that merely mentions one of its words. OR-ing the terms means a pair
        sharing a single incidental word matches at all, so something has to
        stop that from counting as an answer.

        Ordering is done relative to the best match in the same result set rather
        than against a constant, because ``ts_rank_cd`` is not comparable across
        queries: it grows with the number of matched terms, so a longer question
        clears any fixed number that a one-word question never could. Measured
        against the same pair, "orders" scored 1.4 and "how do I track my order"
        scored 3.2. As a fraction of their own best match, the incidental
        third-place pair sits at 0.57 and 0.25 — which *is* comparable, and needs
        no recalibration as the catalog grows.

        That comparison alone can never refuse, though. The best match scores
        1.0 against itself at every setting, so a query whose only matches are
        junk still serves its best piece of junk: "what time does the museum
        close" returned five unrelated pairs tied at 0.4, every one of them
        within any fraction of the best. The absolute floor is the second
        condition — not a ranking, so the incomparability above does not apply,
        but a statement that a match on the answer body alone is not an answer.
        """
        query = cls._tsquery(criteria.query.content)
        rank = func.ts_rank_cd(qa_pairs_table.c.search_vector, query).label(RANK_LABEL)

        matches = select(qa_pairs_table.c.external_id, rank).where(
            qa_pairs_table.c.search_vector.op("@@")(query)
        )
        if criteria.category is not None:
            matches = matches.where(
                qa_pairs_table.c.category == Category(value=criteria.category.value),
            )
        ranked = matches.subquery(MATCHES_SUBQUERY)

        best = select(func.max(ranked.c[RANK_LABEL])).scalar_subquery()

        return (
            select(ranked.c.external_id, ranked.c[RANK_LABEL])
            .where(ranked.c[RANK_LABEL] >= best * relative_floor)
            .where(ranked.c[RANK_LABEL] >= absolute_floor)
            .order_by(ranked.c[RANK_LABEL].desc(), ranked.c.external_id)
            .limit(criteria.top_k.value)
        )
