from collections.abc import Callable
from typing import Final, final, override

from adaptix import P
from adaptix.conversion import get_converter, link, link_function

from answer_service.application.common.ports.mappers.qa_pair_document_mapper import (
    QAPairDocumentMapper,
)
from answer_service.application.common.ports.search import IndexDocument
from answer_service.domain.indexing.entities.qa_pair import QAPair


def _question_of(pair: QAPair) -> str:
    return pair.content.question.content


def _answer_of(pair: QAPair) -> str:
    return pair.content.answer.content


def _category_of(pair: QAPair) -> str:
    return pair.content.category.value


_convert: Final[Callable[[QAPair], IndexDocument]] = get_converter(
    QAPair,
    IndexDocument,
    recipe=[
        link(P[QAPair].id, P[IndexDocument].external_id),
        # adaptix links fields, not paths: ``P[QAPair].content.question.content``
        # is rejected, so each unwrapping goes through its own function.
        link_function(_question_of, P[IndexDocument].question),
        link_function(_answer_of, P[IndexDocument].answer),
        link_function(_category_of, P[IndexDocument].category),
    ],
)


@final
class AdaptixQAPairDocumentMapper(QAPairDocumentMapper):
    """Maps catalog pairs to search documents with an import-time converter.

    Module-level for the same reason as the other adaptix mappers: the retort
    caches the generated code, so a per-instance converter would rebuild it on
    every projection.
    """

    @override
    def to_document(self, pair: QAPair) -> IndexDocument:
        return _convert(pair)
