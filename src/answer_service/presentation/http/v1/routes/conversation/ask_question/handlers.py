import time
from typing import Final

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status

from answer_service.application.common.mediator.sender import Sender
from answer_service.application.queries.conversation.ask_question.query import (
    AskQuestionQuery,
)
from answer_service.presentation.http.v1.common.exception_handler import ExceptionSchema
from answer_service.presentation.http.v1.common.schemas import elapsed_ms

from .schemas import AskRequest, AskSchemaResponse

ask_question_router: Final[APIRouter] = APIRouter(
    tags=["Conversation"],
    route_class=DishkaRoute,
)


@ask_question_router.post(
    "/",
    summary="Answer a question from the catalog, with its sources",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ExceptionSchema},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ExceptionSchema},
    },
)
async def ask_question_handler(
    request: AskRequest,
    sender: FromDishka[Sender],
) -> AskSchemaResponse:
    """Answers a question from the catalog.

    One dispatch: retrieval happens inside the use case, so the question is
    counted once in the reports rather than once as a search and once as an ask.
    """
    started_at = time.perf_counter()
    response = await sender.send(AskQuestionQuery(criteria=request.to_criteria()))
    return AskSchemaResponse.of(request.query, response, elapsed_ms(started_at))
