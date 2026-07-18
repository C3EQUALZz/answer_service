from collections.abc import Iterable
from typing import Final

from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from .get_statistics.handlers import get_statistics_router
from .list_unanswered_queries.handlers import list_unanswered_queries_router

statistics_router: Final[APIRouter] = APIRouter(
    tags=["Statistics"],
    prefix="/statistics",
    route_class=DishkaRoute,
)

_sub_routers: Final[Iterable[APIRouter]] = (
    get_statistics_router,
    list_unanswered_queries_router,
)

for _sub_router in _sub_routers:
    statistics_router.include_router(_sub_router)
