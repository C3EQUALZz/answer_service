import logging
import time
from typing import Final

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status

from answer_service.application.commands.analytics.record_query.command import (
    RecordQueryCommand,
)
from answer_service.application.common.mediator.sender import Sender
from answer_service.application.queries.search.search_qa_pairs.query import (
    SearchQAPairsQuery,
    SearchQAPairsResponse,
)
from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from answer_service.domain.common.error import AppError
from answer_service.domain.search.value_objects.category_filter import CategoryFilter
from answer_service.domain.search.value_objects.search_criteria import SearchCriteria
from answer_service.domain.search.value_objects.search_query import SearchQuery
from answer_service.domain.search.value_objects.top_k import TopK
from answer_service.presentation.http.v1.common.exception_handler import ExceptionSchema

from .schemas import SearchRequest, SearchSchemaResponse

logger: Final[logging.Logger] = logging.getLogger(__name__)

MILLISECONDS_PER_SECOND: Final[int] = 1000

search_qa_pairs_router: Final[APIRouter] = APIRouter(
    tags=["Search"],
    route_class=DishkaRoute,
)


@search_qa_pairs_router.post(
    "/",
    summary="Search the catalog for the entries that answer a question",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ExceptionSchema},
    },
)
async def search_qa_pairs_handler(
    request: SearchRequest,
    sender: FromDishka[Sender],
) -> SearchSchemaResponse:
    """Runs a hybrid search and records the query for the gap report.

    The recording is what makes the statistics endpoints mean anything: an
    unanswered query is only visible as a backlog item because this wrote it
    down.
    """
    started_at = time.perf_counter()

    response = await sender.send(
        SearchQAPairsQuery(
            criteria=SearchCriteria(
                query=SearchQuery(content=request.query),
                top_k=TopK(value=request.top_k),
                category=(
                    CategoryFilter(value=request.category)
                    if request.category is not None
                    else None
                ),
            ),
        ),
    )

    took_ms = round((time.perf_counter() - started_at) * MILLISECONDS_PER_SECOND)
    await _record(sender, request, response, took_ms)

    return SearchSchemaResponse.of(response, took_ms)


async def _record(
    sender: Sender,
    request: SearchRequest,
    response: SearchQAPairsResponse,
    took_ms: int,
) -> None:
    """Logs the served query, and never fails the request it describes.

    The caller already has their results; losing a reporting row is a smaller
    harm than turning a successful search into a 500. The failure is logged at
    exception level so the gap report going quiet is still noticed.
    """
    try:
        await sender.send(
            RecordQueryCommand(
                text=request.query,
                kind=QueryKind.SEARCH,
                results_count=len(response.hits),
                latency_ms=took_ms,
                top_score=response.top_score,
                category=request.category,
            ),
        )
    except AppError:
        logger.exception("search: failed to record the query for reporting")
