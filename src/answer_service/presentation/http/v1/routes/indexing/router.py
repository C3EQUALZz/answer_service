from collections.abc import Iterable
from typing import Final

from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from .enqueue_indexing.handlers import enqueue_indexing_router
from .get_indexing_task.handlers import get_indexing_task_router

indexing_router: Final[APIRouter] = APIRouter(
    tags=["Indexing"],
    prefix="/indexing",
    route_class=DishkaRoute,
)

_sub_routers: Final[Iterable[APIRouter]] = (
    enqueue_indexing_router,
    get_indexing_task_router,
)

for _sub_router in _sub_routers:
    indexing_router.include_router(_sub_router)
