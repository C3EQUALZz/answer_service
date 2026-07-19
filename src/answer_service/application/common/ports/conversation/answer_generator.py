from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from answer_service.application.common.ports.gateways import QAPairView
    from answer_service.domain.conversation.value_objects.answer_text import AnswerText


class AnswerGenerator(Protocol):
    """Writes one answer to a question, using only the pairs it is handed."""

    @abstractmethod
    async def generate(
        self,
        question: str,
        grounding: Sequence[QAPairView],
    ) -> AnswerText:
        """Returns prose answering ``question`` from ``grounding``.

        Never called with empty grounding: an answer with nothing behind it is
        the one thing this service must not produce, and deciding that is the
        caller's job rather than a prompt's.
        """
        raise NotImplementedError
