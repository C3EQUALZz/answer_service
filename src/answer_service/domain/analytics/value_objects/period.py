from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Self, override

from answer_service.domain.analytics.errors import InvalidPeriodError
from answer_service.domain.common.value_object import ValueObject


@dataclass(frozen=True, kw_only=True)
class Period(ValueObject):
    """The half-open time window a report covers: ``[start, end)``.

    Half-open so that consecutive periods tile without double-counting a query
    that lands exactly on a boundary.
    """

    start: datetime
    end: datetime

    @classmethod
    def last_days(cls, days: int, *, now: datetime | None = None) -> Self:
        """Builds the window covering the last *days* days up to now."""
        moment = now if now is not None else datetime.now(UTC)
        return cls(start=moment - timedelta(days=days), end=moment)

    def contains(self, moment: datetime) -> bool:
        return self.start <= moment < self.end

    @override
    def _validate(self) -> None:
        if self.end < self.start:
            msg = f"Period end {self.end} cannot precede its start {self.start}."
            raise InvalidPeriodError(msg)
