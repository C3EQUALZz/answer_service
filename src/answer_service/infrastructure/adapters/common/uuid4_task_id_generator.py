from typing import final, override
from uuid import uuid4

from answer_service.domain.indexing.ports.id_generator import TaskIdGenerator
from answer_service.domain.indexing.value_objects.task_id import TaskId


@final
class UUID4TaskIdGenerator(TaskIdGenerator):
    """Generates task ids client-side, before the row exists.

    The id is needed to schedule the background task in the same transaction
    that persists the task, so it cannot come from a database sequence.
    """

    @override
    def __call__(self) -> TaskId:
        return TaskId(uuid4())
