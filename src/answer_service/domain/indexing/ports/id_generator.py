from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from answer_service.domain.indexing.value_objects.task_id import TaskId


class TaskIdGenerator(Protocol):
    @abstractmethod
    def __call__(self) -> TaskId:
        raise NotImplementedError
