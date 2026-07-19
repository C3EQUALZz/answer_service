from typing import Annotated, Final

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, File, UploadFile, status

from answer_service.application.commands.indexing.enqueue_indexing.command import (
    EnqueueIndexingCommand,
)
from answer_service.application.common.mediator.sender import Sender
from answer_service.presentation.http.v1.common.exception_handler import (
    ExceptionSchema,
    ExceptionSchemaRich,
)
from answer_service.presentation.http.v1.routes.indexing.enqueue_indexing.schemas import (
    EnqueueIndexingResponse,
)

enqueue_indexing_router: Final[APIRouter] = APIRouter(
    tags=["Indexing"],
    route_class=DishkaRoute,
)

SourceFile = File(
    title="Source file",
    description="CSV or Excel document holding the question-answer pairs",
)


@enqueue_indexing_router.post(
    "/index/sync",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a source file and schedule a synchronization",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ExceptionSchema},
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {"model": ExceptionSchema},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ExceptionSchemaRich},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ExceptionSchema},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ExceptionSchema},
    },
)
async def enqueue_indexing_handler(
    file: Annotated[UploadFile, SourceFile],
    sender: FromDishka[Sender],
) -> EnqueueIndexingResponse:
    """Accepts the upload and returns a task to poll.

    202 rather than 200: the file is validated and stored synchronously, but the
    synchronization itself runs in the background and may take minutes.
    """
    response = await sender.send(
        EnqueueIndexingCommand(
            content=await file.read(),
            filename=file.filename or "",
            content_type=file.content_type,
        ),
    )
    return EnqueueIndexingResponse(
        task_id=response.task_id,
        status=response.status.value,
    )
