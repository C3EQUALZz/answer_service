from typing import Annotated, Final

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Query, status

from answer_service.application.common.mediator.sender import Sender
from answer_service.application.common.query_params.pagination import Pagination
from answer_service.application.common.query_params.sorting import SortingOrder
from answer_service.application.queries.analytics.list_unanswered_queries.query import (
    ListUnansweredQueriesQuery,
)
from answer_service.domain.analytics.value_objects.period import Period
from answer_service.presentation.http.v1.common.exception_handler import ExceptionSchema

from .schemas import UnansweredQueriesSchemaResponse

MIN_DAYS: Final[int] = 1
MAX_DAYS: Final[int] = 365
DEFAULT_DAYS: Final[int] = 30
MIN_LIMIT: Final[int] = 1
MAX_LIMIT: Final[int] = 200
DEFAULT_LIMIT: Final[int] = 20

list_unanswered_queries_router: Final[APIRouter] = APIRouter(
    tags=["Statistics"],
    route_class=DishkaRoute,
)

DaysQuery = Query(
    title="Period length",
    description="How many days back to look for unanswered queries",
    ge=MIN_DAYS,
    le=MAX_DAYS,
)

LimitQuery = Query(
    title="Limit",
    description="How many distinct queries to return",
    ge=MIN_LIMIT,
    le=MAX_LIMIT,
)

OffsetQuery = Query(
    title="Offset",
    description="How many entries of the backlog to skip",
    ge=0,
)


@list_unanswered_queries_router.get(
    "/unanswered",
    summary="Questions the catalog could not answer",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ExceptionSchema},
    },
)
async def list_unanswered_queries_handler(
    sender: FromDishka[Sender],
    days: Annotated[int, DaysQuery] = DEFAULT_DAYS,
    limit: Annotated[int, LimitQuery] = DEFAULT_LIMIT,
    offset: Annotated[int, OffsetQuery] = 0,
    sorting_order: SortingOrder = SortingOrder.DESC,
) -> UnansweredQueriesSchemaResponse:
    """The actionable half of the report: each entry is an FAQ entry to write."""
    response = await sender.send(
        ListUnansweredQueriesQuery(
            period=Period.last_days(days),
            pagination=Pagination(limit=limit, offset=offset),
            sorting_order=sorting_order,
        ),
    )
    return UnansweredQueriesSchemaResponse.of(response)
