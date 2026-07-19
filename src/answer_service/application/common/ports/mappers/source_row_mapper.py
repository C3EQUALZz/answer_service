from abc import abstractmethod
from typing import Protocol

from answer_service.application.common.ports.source_file.source_row import SourceRow
from answer_service.domain.indexing.value_objects.desired_pair import DesiredPair


class SourceRowMapper(Protocol):
    """Turns a raw source-file row into the desired state of one catalog pair.

    The row's fields are untyped strings straight from the customer's file, so
    this is where they first meet the value objects that validate them: a blank
    question or an empty external id is refused here, before the sync planner
    ever sees the pair.
    """

    @abstractmethod
    def to_desired_pair(self, row: SourceRow) -> DesiredPair:
        raise NotImplementedError
