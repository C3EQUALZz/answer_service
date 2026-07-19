from dataclasses import dataclass

from answer_service.application.common.mediator.markers import Command
from answer_service.domain.indexing.value_objects.external_id import ExternalId


@dataclass(frozen=True, slots=True)
class RemoveQAPairCommand(Command[None]):
    """Clears a QA pair from the search index."""

    external_id: ExternalId
