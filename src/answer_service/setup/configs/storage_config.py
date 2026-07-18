from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class StorageConfig:
    """Where uploaded source files are staged between request and worker.

    The HTTP request writes the upload here and hands the worker a reference;
    the worker reads it back, possibly minutes later and possibly in another
    process. The directory must therefore be shared by both — a container-local
    path works only while they run in the same container.

    Attributes:
        directory: Directory holding the staged uploads.
    """

    directory: Path = Path("var/uploads")
