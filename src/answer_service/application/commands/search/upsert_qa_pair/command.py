from dataclasses import dataclass

from answer_service.application.common.mediator.markers import Command
from answer_service.domain.indexing.value_objects.external_id import ExternalId


@dataclass(frozen=True, slots=True)
class UpsertQAPairCommand(Command[None]):
    """Writes a QA pair's current state into the search index.

    Dispatched for the catalog events that create or change a pair. Carries only
    the identity: the handler reads the pair itself rather than trusting the
    event to describe it.
    """

    external_id: ExternalId
