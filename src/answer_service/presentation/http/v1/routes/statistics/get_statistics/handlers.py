from typing import Annotated, Final

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Query

from answer_service.application.common.mediator.sender import Sender
from answer_service.application.queries.analytics.get_statistics.query import (
    GetStatisticsQuery,
)
from answer_service.domain.analytics.value_objects.period import Period
from answer_service.presentation.http.v1.routes.statistics.get_statistics.schemas import (
    StatisticsSchemaResponse,
)

MIN_DAYS: Final[int] = 1
MAX_DAYS: Final[int] = 365
DEFAULT_DAYS: Final[int] = 30

get_statistics_router: Final[APIRouter] = APIRouter(
    tags=["Statistics"],
    route_class=DishkaRoute,
)

DaysQuery = Query(
    title="Period length",
    description="How many days back the query half of the report covers",
    ge=MIN_DAYS,
    le=MAX_DAYS,
)


@get_statistics_router.get(
    "/",
    summary="Catalog size and query usage for a period",
)
async def get_statistics_handler(
    sender: FromDishka[Sender],
    days: Annotated[int, DaysQuery] = DEFAULT_DAYS,
) -> StatisticsSchemaResponse:
    """The catalog half is always as of now — a QA pair has no history."""
    response = await sender.send(GetStatisticsQuery(period=Period.last_days(days)))
    return StatisticsSchemaResponse.of(response)
