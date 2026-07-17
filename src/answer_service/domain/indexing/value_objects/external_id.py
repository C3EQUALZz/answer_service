from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.indexing.errors import EmptyExternalIdError


@dataclass(frozen=True, kw_only=True)
class ExternalId(ValueObject):
    """Stable, source-provided unique identifier of a QA pair."""

    value: str

    @override
    def _validate(self) -> None:
        if not self.value.strip():
            msg = "external_id cannot be empty."
            raise EmptyExternalIdError(msg)

    def __str__(self) -> str:
        return self.value
