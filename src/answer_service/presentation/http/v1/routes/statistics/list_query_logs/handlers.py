from typing import Annotated, Final

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Query, status

from answer_service.application.common.mediator.sender import Sender
from answer_service.application.common.query_params.pagination import Pagination
from answer_service.application.common.query_params.sorting import SortingOrder
from answer_service.application.queries.analytics.list_query_logs.query import (
    ListQueryLogsQuery,
)
from answer_service.domain.analytics.value_objects.period import Period
from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from answer_service.domain.analytics.value_objects.query_status import QueryStatus
from answer_service.presentation.http.v1.common.exception_handler import (
    ExceptionSchema,
    ExceptionSchemaRich,
)

from .schemas import QueryLogsSchemaResponse

MIN_DAYS: Final[int] = 1
MAX_DAYS: Final[int] = 365
DEFAULT_DAYS: Final[int] = 30
MIN_LIMIT: Final[int] = 1
MAX_LIMIT: Final[int] = 200
DEFAULT_LIMIT: Final[int] = 20

list_query_logs_router: Final[APIRouter] = APIRouter(
    tags=["Statistics"],
    route_class=DishkaRoute,
)

DaysQuery = Query(
    title="Period length",
    description="How many days back the journal covers",
    ge=MIN_DAYS,
    le=MAX_DAYS,
)

KindQuery = Query(
    title="Operation type",
    description="Restrict to search or ask requests",
)

StatusQuery = Query(
    title="Execution status",
    description="Restrict to successful or failed requests",
)

LimitQuery = Query(
    title="Limit",
    description="How many entries to return",
    ge=MIN_LIMIT,
    le=MAX_LIMIT,
)

OffsetQuery = Query(
    title="Offset",
    description="How many entries to skip",
    ge=0,
)


@list_query_logs_router.get(
    "/queries",
    summary="The recorded search and ask requests, most recent first",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ExceptionSchemaRich},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ExceptionSchema},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ExceptionSchema},
    },
)
async def list_query_logs_handler(
    sender: FromDishka[Sender],
    days: Annotated[int, DaysQuery] = DEFAULT_DAYS,
    kind: Annotated[QueryKind | None, KindQuery] = None,
    query_status: Annotated[QueryStatus | None, StatusQuery] = None,
    limit: Annotated[int, LimitQuery] = DEFAULT_LIMIT,
    offset: Annotated[int, OffsetQuery] = 0,
    sorting_order: SortingOrder = SortingOrder.DESC,
) -> QueryLogsSchemaResponse:
    """The audit half of the statistics: one row per served request.

    Every filter §10 asks for maps to one query parameter — period via ``days``,
    operation via ``kind``, success via ``query_status`` — and the order is over
    ``occurred_at``, the time the request arrived.
    """
    response = await sender.send(
        ListQueryLogsQuery(
            period=Period.last_days(days),
            kind=kind,
            status=query_status,
            pagination=Pagination(limit=limit, offset=offset),
            sorting_order=sorting_order,
        ),
    )
    return QueryLogsSchemaResponse.of(response)
