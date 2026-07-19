from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field

from answer_service.application.queries.conversation.ask_question.query import (
    AskQuestionResponse,
)
from answer_service.domain.search.value_objects.top_k import MAX_TOP_K, MIN_TOP_K
from answer_service.presentation.http.v1.common.schemas import CriteriaRequest

DEFAULT_TOP_K: int = 3


class AskRequest(CriteriaRequest):
    """The question, and how much of the catalog to ground the answer in."""

    top_k: Annotated[
        int,
        Field(
            ge=MIN_TOP_K,
            le=MAX_TOP_K,
            description="How many catalog entries the answer may draw on",
        ),
    ] = DEFAULT_TOP_K


class SourceSchema(BaseModel):
    """A catalog entry the answer was drawn from."""

    external_id: str
    question: str
    category: str


class AskSchemaResponse(BaseModel):
    """The answer and what it stands on.

    ``answer`` is null when the catalog held nothing relevant. That is a real
    outcome rather than an error: it is what the gap report is built from, and
    saying nothing beats inventing a policy in the operator's voice.
    """

    request_id: UUID
    query: str
    answer: str | None
    sources: list[SourceSchema]
    duration_ms: int

    @classmethod
    def of(
        cls,
        request_id: UUID,
        question: str,
        response: AskQuestionResponse,
        duration_ms: int,
    ) -> Self:
        cited = (
            {source.value for source in response.answer.sources}
            if response.answer is not None
            else set()
        )
        return cls(
            request_id=request_id,
            query=question,
            answer=(
                response.answer.text.content if response.answer is not None else None
            ),
            sources=[
                SourceSchema(
                    external_id=hit.pair.external_id,
                    question=hit.pair.question,
                    category=hit.pair.category,
                )
                for hit in response.grounding
                if hit.pair.external_id in cited
            ],
            duration_ms=duration_ms,
        )
