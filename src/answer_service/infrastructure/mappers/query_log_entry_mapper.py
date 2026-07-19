from abc import abstractmethod
from typing import Any, Protocol

from sqlalchemy import Row

from answer_service.application.common.ports.gateways import QueryLogEntry


class QueryLogEntryMapper(Protocol):
    """Builds one journal listing row from a result row.

    In the infrastructure layer, port and all, for the same reason as the task
    view mapper: its input is a ``sqlalchemy.Row``, and declaring that among
    the application ports would put the ORM in the layer meant not to know one.
    """

    @abstractmethod
    def to_entry(self, row: Row[Any]) -> QueryLogEntry:
        raise NotImplementedError
