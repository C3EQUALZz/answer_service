from collections.abc import Iterable
from typing import Final

from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from .search_qa_pairs.handlers import search_qa_pairs_router

search_router: Final[APIRouter] = APIRouter(
    tags=["Search"],
    route_class=DishkaRoute,
)

_sub_routers: Final[Iterable[APIRouter]] = (search_qa_pairs_router,)

for _sub_router in _sub_routers:
    search_router.include_router(_sub_router)
