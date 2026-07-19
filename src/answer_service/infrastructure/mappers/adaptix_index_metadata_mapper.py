from typing import Final, final, override

from adaptix import Retort, dumper

from answer_service.application.common.ports.search import IndexDocument
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.infrastructure.mappers.index_metadata_mapper import (
    IndexMetadataMapper,
)


def _external_id_str(external_id: ExternalId) -> str:
    return external_id.value


_retort: Final[Retort] = Retort(recipe=[dumper(ExternalId, _external_id_str)])


@final
class AdaptixIndexMetadataMapper(IndexMetadataMapper):
    """Dumps the document's fields as the Qdrant payload.

    The payload keys are the document's own field names, which is what keeps
    the dense retriever's ``metadata['external_id']`` lookup and this writer
    from drifting: adding a field to ``IndexDocument`` carries it across
    without a second edit here.
    """

    @override
    def to_metadata(self, document: IndexDocument) -> dict[str, str]:
        metadata: dict[str, str] = _retort.dump(document)
        return metadata
