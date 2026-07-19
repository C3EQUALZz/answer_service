import time
from typing import Final

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status

from answer_service.application.common.mediator.sender import Sender
from answer_service.application.queries.search.search_qa_pairs.query import (
    SearchQAPairsQuery,
)
from answer_service.presentation.http.v1.common.exception_handler import (
    ExceptionSchema,
    ExceptionSchemaRich,
)
from answer_service.presentation.http.v1.common.schemas import elapsed_ms

from .schemas import SearchRequest, SearchSchemaResponse

search_qa_pairs_router: Final[APIRouter] = APIRouter(
    tags=["Search"],
    route_class=DishkaRoute,
)


@search_qa_pairs_router.post(
    "/",
    summary="Search the catalog for the entries that answer a question",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ExceptionSchema},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ExceptionSchemaRich},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ExceptionSchema},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ExceptionSchema},
    },
)
async def search_qa_pairs_handler(
    request: SearchRequest,
    sender: FromDishka[Sender],
) -> SearchSchemaResponse:
    """Runs a hybrid search.

    The query is journalled for the reports by the recording pipeline, not from
    here: statistics that depend on a route remembering to write a row are
    statistics that quietly under-report.
    """
    started_at = time.perf_counter()
    response = await sender.send(SearchQAPairsQuery(criteria=request.to_criteria()))
    return SearchSchemaResponse.of(response, elapsed_ms(started_at))
