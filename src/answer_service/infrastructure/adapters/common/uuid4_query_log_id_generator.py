from typing import final, override
from uuid import uuid4

from answer_service.domain.analytics.ports.id_generator import QueryLogIdGenerator
from answer_service.domain.analytics.value_objects.query_log_id import QueryLogId


@final
class UUID4QueryLogIdGenerator(QueryLogIdGenerator):
    """Generates query log ids."""

    @override
    def __call__(self) -> QueryLogId:
        return QueryLogId(uuid4())
