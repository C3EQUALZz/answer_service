from enum import StrEnum


class SourceKind(StrEnum):
    """Backend a configuration is read from.

    Used as a typed flag (from env/CLI/config) so the DI container can select
    the matching :class:`SourceFactory`. Adding a value here is a reminder to
    wire a factory for it; some backends need an extra install
    (``dature[toml]``, ``dature[yaml]``, ``dature[vault]``).
    """

    ENV = "env"
    ENV_FILE = "env_file"
    JSON = "json"
    TOML = "toml"
    YAML = "yaml"
    VAULT = "vault"
