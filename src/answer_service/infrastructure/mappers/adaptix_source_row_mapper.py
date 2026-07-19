from collections.abc import Callable
from typing import Final, final, override

from adaptix import P
from adaptix.conversion import coercer, get_converter, link, link_function

from answer_service.application.common.ports.mappers.source_row_mapper import (
    SourceRowMapper,
)
from answer_service.application.common.ports.source_file.source_row import SourceRow
from answer_service.domain.indexing.value_objects.answer import Answer
from answer_service.domain.indexing.value_objects.category import Category
from answer_service.domain.indexing.value_objects.desired_pair import DesiredPair
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.qa_content import QAContent
from answer_service.domain.indexing.value_objects.question import Question


def _external_id_of(value: str) -> ExternalId:
    return ExternalId(value=value)


def _content_of(row: SourceRow) -> QAContent:
    """Builds the grouped payload the row has no single field for.

    ``QAContent`` exists so change detection is one value comparison, which
    means three flat columns have to become one nested object — adaptix links
    fields, not shapes, so this is the seam where that happens.
    """
    return QAContent(
        question=Question(content=row.question),
        answer=Answer(content=row.answer),
        category=Category(value=row.category),
    )


_convert: Final[Callable[[SourceRow], DesiredPair]] = get_converter(
    SourceRow,
    DesiredPair,
    recipe=[
        coercer(str, ExternalId, _external_id_of),
        link(P[SourceRow].updated_at, P[DesiredPair].source_updated_at),
        link_function(_content_of, P[DesiredPair].content),
    ],
)


@final
class AdaptixSourceRowMapper(SourceRowMapper):
    """Maps source rows with a converter compiled once, at import time.

    The converter is built at module level rather than per instance: adaptix
    generates and caches code on the retort, so constructing one in ``__init__``
    would recompile the mapping for every request that resolves this.

    A malformed recipe therefore fails when the container is built, not on the
    first row of a sync run that has already been accepted.
    """

    @override
    def to_desired_pair(self, row: SourceRow) -> DesiredPair:
        return _convert(row)
