from typing import Final

PORT_MIN: Final[int] = 1
PORT_MAX: Final[int] = 65535

POOL_SIZE_MIN: Final[int] = 1
POOL_SIZE_MAX: Final[int] = 1000
POOL_RECYCLE_MIN: Final[int] = 1
POOL_OVERFLOW_MIN: Final[int] = 0

REDIS_DB_MIN: Final[int] = 0
REDIS_DB_MAX: Final[int] = 15

RETRY_COUNT_MIN: Final[int] = 0
DELAY_MIN: Final[float] = 0.0
MAX_DELAY_EXPONENT_MIN: Final[float] = 1.0

TEMPERATURE_MIN: Final[float] = 0.0
TEMPERATURE_MAX: Final[float] = 2.0
