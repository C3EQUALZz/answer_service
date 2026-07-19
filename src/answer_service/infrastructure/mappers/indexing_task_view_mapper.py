from abc import abstractmethod
from typing import Any, Protocol

from sqlalchemy import Row

from answer_service.application.common.ports.gateways import IndexingTaskView


class IndexingTaskViewMapper(Protocol):
    """Builds the task status read model from a result row.

    Kept in the infrastructure layer, port and all, because its input is a
    ``sqlalchemy.Row``: declaring this among the application ports would put
    the ORM in the layer that is meant not to know one.
    """

    @abstractmethod
    def to_view(self, row: Row[Any]) -> IndexingTaskView:
        raise NotImplementedError
