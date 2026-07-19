import logging
from typing import Final, override

from answer_service.application.common.mediator.handlers import QueryHandler
from answer_service.application.common.ports.conversation import AnswerGenerator
from answer_service.application.common.services import HybridSearchService
from answer_service.application.queries.conversation.ask_question.query import (
    AskQuestionQuery,
    AskQuestionResponse,
)
from answer_service.domain.conversation.value_objects.grounded_answer import (
    GroundedAnswer,
)
from answer_service.domain.indexing.value_objects.external_id import ExternalId

logger: Final[logging.Logger] = logging.getLogger(__name__)


class AskQuestionHandler(QueryHandler[AskQuestionQuery, AskQuestionResponse]):
    """Retrieves, then turns what it retrieved into one answer — or declines.

    Nothing retrieved means no answer and no model call. That is the whole
    safeguard: a language model asked to answer from an empty context will
    happily answer from its own training instead, and an invented refund policy
    delivered in the operator's voice is worse than a blank page. The empty
    result is returned rather than raised, because a question the catalog cannot
    answer is exactly what the gap report is built from.
    """

    def __init__(
        self,
        hybrid_search: HybridSearchService,
        answer_generator: AnswerGenerator,
    ) -> None:
        self._hybrid_search: Final[HybridSearchService] = hybrid_search
        self._answer_generator: Final[AnswerGenerator] = answer_generator

    @override
    async def handle(self, query: AskQuestionQuery) -> AskQuestionResponse:
        grounding = await self._hybrid_search.search(query.criteria)

        if not grounding:
            logger.info("ask: nothing retrieved, declining to answer")
            return AskQuestionResponse(answer=None, grounding=())

        text = await self._answer_generator.generate(
            query.criteria.query.content,
            [hit.pair for hit in grounding],
        )

        return AskQuestionResponse(
            answer=GroundedAnswer(
                text=text,
                sources=tuple(
                    ExternalId(value=hit.pair.external_id) for hit in grounding
                ),
            ),
            grounding=grounding,
        )
