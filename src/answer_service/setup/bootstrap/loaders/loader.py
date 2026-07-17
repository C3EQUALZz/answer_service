from abc import abstractmethod
from typing import Protocol


class ConfigLoader[ConfigT](Protocol):
    """Produces a fully-built, validated configuration object.

    The interface is deliberately agnostic of *how* the config is obtained.
    """

    @abstractmethod
    def load(self) -> ConfigT:
        """Read, convert and validate the configuration."""
        ...
