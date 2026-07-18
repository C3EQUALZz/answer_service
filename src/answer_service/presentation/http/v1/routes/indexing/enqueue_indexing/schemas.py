from uuid import UUID

from pydantic import BaseModel


class EnqueueIndexingResponse(BaseModel):
    """The accepted upload: a task exists, the work has not started."""

    task_id: UUID
    status: str
