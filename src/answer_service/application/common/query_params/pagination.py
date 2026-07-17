from dataclasses import dataclass

from answer_service.application.error import PaginationError


@dataclass(frozen=True, slots=True, kw_only=True)
class Pagination:
    limit: int | None = None
    offset: int | None = None

    def __post_init__(self) -> None:
        if self.limit is not None and self.limit <= 0:
            msg = f"Limit must be greater than 0, got {self.limit}."
            raise PaginationError(msg)
        if self.offset is not None and self.offset < 0:
            msg = f"Offset must be non-negative, got {self.offset}."
            raise PaginationError(msg)
