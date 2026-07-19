from collections.abc import Iterable
from typing import Final

from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from .ask_question.handlers import ask_question_router

conversation_router: Final[APIRouter] = APIRouter(
    tags=["Conversation"],
    prefix="/ask",
    route_class=DishkaRoute,
)

_sub_routers: Final[Iterable[APIRouter]] = (ask_question_router,)

for _sub_router in _sub_routers:
    conversation_router.include_router(_sub_router)
