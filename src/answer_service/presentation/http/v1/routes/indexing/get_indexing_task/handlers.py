from typing import Annotated, Final
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Path, status

from answer_service.application.common.mediator.sender import Sender
from answer_service.application.queries.indexing.get_indexing_task.query import (
    GetIndexingTaskQuery,
)
from answer_service.domain.indexing.value_objects.task_id import TaskId
from answer_service.presentation.http.v1.common.exception_handler import ExceptionSchema

from .schemas import IndexingTaskResponse

get_indexing_task_router: Final[APIRouter] = APIRouter(
    tags=["Indexing"],
    route_class=DishkaRoute,
)

TaskIdPath = Path(
    title="Task ID",
    description="Identifier returned when the source file was uploaded",
    examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
)


@get_indexing_task_router.get(
    "/tasks/{task_id}",
    summary="Read the status of a synchronization run",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ExceptionSchema},
    },
)
async def get_indexing_task_handler(
    task_id: Annotated[UUID, TaskIdPath],
    sender: FromDishka[Sender],
) -> IndexingTaskResponse:
    """Clients poll this until ``is_finished`` turns true."""
    view = await sender.send(GetIndexingTaskQuery(task_id=TaskId(task_id)))
    return IndexingTaskResponse.of(view)
