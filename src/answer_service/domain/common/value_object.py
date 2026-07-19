import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Final

from .error import DomainError

logger: Final[logging.Logger] = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ValueObject(ABC):
    """Base for every value object, validated the moment it is constructed.

    Rejections are logged here rather than in each subclass. A value object
    refusing a value is how bad input is turned away, and it happens in the
    middle of a use case where the caller only sees the raised error — one line
    at the point of refusal says which value object rejected what, for every one
    of them, without a log call in forty files.

    Debug level because rejection is ordinary traffic: a blank search query is
    someone typing spaces, not an incident.
    """

    def __post_init__(self) -> None:
        try:
            self._validate()
        except DomainError:
            logger.debug("%s rejected the value it was given", type(self).__name__)
            raise

    @abstractmethod
    def _validate(self) -> None: ...
