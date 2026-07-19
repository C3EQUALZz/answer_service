from dataclasses import dataclass
from typing import Final

REDIS_SCHEME: Final[str] = "redis"


@dataclass(slots=True, frozen=True)
class RedisConfig:
    """Connection settings for the Redis instance backing taskiq.

    Plain stdlib dataclass with no dependency on the config loader: the env
    mapping and validation live in
    ``answer_service.setup.bootstrap.loaders.redis_config_loader``.

    Three logical databases on one server: results, schedules and cache are
    unrelated data with different lifetimes, and separating them keeps a
    ``FLUSHDB`` of one from taking the others with it.

    Attributes:
        host: Redis server hostname or IP address.
        port: Redis server port.
        user: ACL username. Empty falls back to the ``default`` user, which
            carries every permission — name a scoped user in production.
        password: Password, empty when the server requires no auth.
        worker_db: Database index for the taskiq result backend.
        schedule_source_db: Database index for the taskiq schedule source.
        cache_db: Database index for the application cache.

    Properties:
        worker_uri: Connection URI for the result backend.
        schedule_source_uri: Connection URI for the schedule source.
        cache_uri: Connection URI for the application cache.
    """

    host: str
    port: int
    user: str = ""
    password: str = ""
    worker_db: int = 1
    schedule_source_db: int = 2
    cache_db: int = 0

    @property
    def worker_uri(self) -> str:
        """URI of the database holding task results."""
        return self._uri(self.worker_db)

    @property
    def schedule_source_uri(self) -> str:
        """URI of the database holding scheduled tasks."""
        return self._uri(self.schedule_source_db)

    @property
    def cache_uri(self) -> str:
        """URI of the database holding the application cache."""
        return self._uri(self.cache_db)

    def _uri(self, db: int) -> str:
        """Builds one database's URI.

        The username is omitted when unset so the server applies ``default``;
        sending an empty username would be rejected outright rather than
        falling back.
        """
        if not self.password:
            return f"{REDIS_SCHEME}://{self.host}:{self.port}/{db}"
        return (
            f"{REDIS_SCHEME}://{self.user}:{self.password}@{self.host}:{self.port}/{db}"
        )
