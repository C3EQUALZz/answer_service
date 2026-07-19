from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.conversation.errors import UngroundedAnswerError
from answer_service.domain.conversation.value_objects.answer_text import AnswerText
from answer_service.domain.indexing.value_objects.external_id import ExternalId


@dataclass(frozen=True, kw_only=True)
class GroundedAnswer(ValueObject):
    """An answer together with the catalog entries it was drawn from.

    The sources are not decoration. An answer with none of them is either
    invented or copied from the model's own training, and this service exists to
    answer *from a catalog* — so the pairing is enforced rather than assumed.

    Sources are identities only; their text is joined by the application layer,
    the same way the search context ranks identities and leaves the text alone.
    """

    text: AnswerText
    sources: tuple[ExternalId, ...]

    @override
    def _validate(self) -> None:
        if not self.sources:
            msg = "An answer must cite at least one catalog entry."
            raise UngroundedAnswerError(msg)
