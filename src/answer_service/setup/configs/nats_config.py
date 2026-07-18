from dataclasses import dataclass
from typing import Final

NATS_SCHEME: Final[str] = "nats"


@dataclass(slots=True, frozen=True)
class NatsConfig:
    """Connection settings for the NATS server backing the task broker.

    Plain stdlib dataclass with no dependency on the config loader: the env
    mapping and validation live in
    ``answer_service.setup.bootstrap.loaders.nats_config_loader``.

    Attributes:
        host: NATS server hostname or IP address.
        port: NATS server port.
        user: Username, empty when the server allows anonymous connections.
        password: Password for ``user``.

    Properties:
        uri: Complete ``nats://`` connection URI.
    """

    host: str
    port: int
    user: str = ""
    password: str = ""

    @property
    def uri(self) -> str:
        """Builds the NATS connection URI.

        Credentials are omitted entirely when ``user`` is empty, so an
        unauthenticated local server does not receive an empty ``@`` prefix it
        would reject.
        """
        if not self.user:
            return f"{NATS_SCHEME}://{self.host}:{self.port}"
        return f"{NATS_SCHEME}://{self.user}:{self.password}@{self.host}:{self.port}"
