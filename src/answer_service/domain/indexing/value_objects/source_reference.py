from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.indexing.errors import EmptySourceReferenceError


@dataclass(frozen=True, kw_only=True)
class SourceReference(ValueObject):
    """Opaque reference to the stored source file a sync run reads from.

    The domain treats it as an identity string; only the storage adapter knows
    it is a path / object key.
    """

    value: str

    @override
    def _validate(self) -> None:
        if not self.value.strip():
            msg = "source reference cannot be empty."
            raise EmptySourceReferenceError(msg)

    def __str__(self) -> str:
        return self.value
