from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from answer_service.domain.analytics.value_objects.query_log_id import QueryLogId


class QueryLogIdGenerator(Protocol):
    @abstractmethod
    def __call__(self) -> QueryLogId:
        raise NotImplementedError
