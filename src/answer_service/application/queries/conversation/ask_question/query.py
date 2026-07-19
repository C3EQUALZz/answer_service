from dataclasses import dataclass
from typing import override

from answer_service.application.common.analytics import RecordableQuery
from answer_service.application.common.services import SearchHit
from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from answer_service.domain.conversation.value_objects.grounded_answer import (
    GroundedAnswer,
)
from answer_service.domain.search.value_objects.search_criteria import SearchCriteria


@dataclass(frozen=True, slots=True)
class AskQuestionResponse:
    """The generated answer, and the pairs it was written from.

    The grounding is reported alongside the answer rather than folded into it:
    the answer cites identities, and a caller showing sources needs their text.
    It is also what the journal counts, so a question that retrieved nothing is
    recorded as unanswered rather than not recorded at all.
    """

    answer: GroundedAnswer | None
    grounding: tuple[SearchHit, ...]

    @property
    def is_answered(self) -> bool:
        return self.answer is not None

    @property
    def results_count(self) -> int:
        return len(self.grounding)

    @property
    def top_score(self) -> float | None:
        if not self.grounding:
            return None
        return self.grounding[0].result.scores.final.value


@dataclass(frozen=True)
class AskQuestionQuery(RecordableQuery[AskQuestionResponse]):
    """Answers a question from the catalog, retrieving what it needs itself.

    Carries search criteria rather than pre-retrieved pairs: asking is one use
    case and must be one dispatch. Retrieval is shared with ``/v1/search``
    through ``HybridSearchService``, so the two cannot disagree about what the
    catalog holds, while the journal still sees exactly one served query.
    """

    criteria: SearchCriteria

    @property
    @override
    def journalled_text(self) -> str:
        return self.criteria.query.content

    @property
    @override
    def journalled_kind(self) -> QueryKind:
        return QueryKind.ASK

    @property
    @override
    def journalled_category(self) -> str | None:
        if self.criteria.category is None:
            return None
        return self.criteria.category.value
