import logging
from typing import TYPE_CHECKING, Final, final, override

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from answer_service.application.common.ports.conversation import AnswerGenerator
from answer_service.domain.conversation.value_objects.answer_text import AnswerText
from answer_service.infrastructure.errors import AnswerGenerationError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from answer_service.application.common.ports.gateways import QAPairView

logger: Final[logging.Logger] = logging.getLogger(__name__)

SYSTEM_PROMPT: Final[str] = (
    "You answer questions about a product using only the question-answer pairs "
    "provided below. Write one short, direct answer in the user's own language. "
    "Use only what the pairs state: if they do not cover the question, say so "
    "plainly instead of guessing, and never invent policies, prices or steps. "
    "Do not mention the pairs, their numbering, or that you were given context."
)


@final
class LangChainAnswerGenerator(AnswerGenerator):
    """Generates the answer with the configured chat model.

    Grounding is passed as the whole retrieved pair, question and answer both:
    the stored answer is what the operator wrote and wants said, and the stored
    question is what tells the model which of several pairs the user meant.
    """

    def __init__(self, chat_model: BaseChatModel) -> None:
        self._chat_model: Final[BaseChatModel] = chat_model

    @override
    async def generate(
        self,
        question: str,
        grounding: Sequence[QAPairView],
    ) -> AnswerText:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=self._prompt(question, grounding)),
        ]

        try:
            response = await self._chat_model.ainvoke(messages)
        except Exception as e:
            msg = "The chat model failed to generate an answer."
            raise AnswerGenerationError(msg) from e

        return AnswerText(content=self._text_of(response.content))

    @staticmethod
    def _prompt(question: str, grounding: Sequence[QAPairView]) -> str:
        pairs = "\n\n".join(f"Q: {pair.question}\nA: {pair.answer}" for pair in grounding)
        return f"{pairs}\n\nUser question: {question}"

    @staticmethod
    def _text_of(content: object) -> str:
        """Flattens the several shapes a chat model may answer in.

        ``content`` is a plain string for most models but a list of content
        blocks when one streams or returns structured parts; joining the text
        blocks keeps the adapter from depending on which.
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(part for part in content if isinstance(part, str))
        return str(content)
