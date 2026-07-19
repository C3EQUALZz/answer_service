"""The loaders for the infrastructure configs.

A config that loads wrong fails at startup with a confusing message, or worse,
starts and points the service at the wrong place. These check the validation
rules and the derived connection strings — the parts that are ours rather than
dature's.
"""

import pytest
from dature.errors.exceptions import DatureConfigError

from answer_service.setup.bootstrap.loaders.mistral_config_loader import (
    MistralConfigLoader,
)
from answer_service.setup.bootstrap.loaders.nats_config_loader import NatsConfigLoader
from answer_service.setup.bootstrap.loaders.qdrant_config_loader import (
    QdrantConfigLoader,
)
from answer_service.setup.bootstrap.loaders.redis_config_loader import RedisConfigLoader
from answer_service.setup.bootstrap.loaders.storage_config_loader import (
    StorageConfigLoader,
)
from answer_service.setup.bootstrap.loaders.taskiq_config_loader import (
    TaskIQConfigLoader,
)
from tests.unit.factories.source_stubs import (
    mistral_source_stub,
    nats_source_stub,
    qdrant_source_stub,
    redis_source_stub,
    storage_source_stub,
    taskiq_source_stub,
)
from tests.unit.support import render_exception


def test_nats_builds_an_anonymous_uri_when_no_user_is_set() -> None:
    """An empty user must not leave a stray ``@`` the server would reject."""
    config = NatsConfigLoader(nats_source_stub()).load()

    assert config.uri == "nats://localhost:4222"


def test_nats_includes_credentials_when_a_user_is_set() -> None:
    stub = nats_source_stub(NATS_USER="app", NATS_PASSWORD="s3cr3t")

    config = NatsConfigLoader(stub).load()

    assert config.uri == "nats://app:s3cr3t@localhost:4222"


@pytest.mark.parametrize("port", ("0", "65536", "-1"))
def test_nats_rejects_a_port_outside_the_valid_range(port: str) -> None:
    loader = NatsConfigLoader(nats_source_stub(NATS_PORT=port))

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "NATS_PORT must be between 1 and 65535" in render_exception(excinfo.value)


def test_nats_password_is_masked_in_error_output() -> None:
    stub = nats_source_stub(NATS_PASSWORD="TOP-SECRET-VALUE", NATS_PORT="999999")

    loader = NatsConfigLoader(stub)

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "TOP-SECRET-VALUE" not in render_exception(excinfo.value)


def test_redis_gives_each_purpose_its_own_database() -> None:
    """Results and schedules must not share a database, or a flush takes both."""
    config = RedisConfigLoader(redis_source_stub()).load()

    assert config.worker_uri == "redis://localhost:6379/1"
    assert config.schedule_source_uri == "redis://localhost:6379/2"
    assert config.cache_uri == "redis://localhost:6379/0"


def test_redis_includes_the_password_when_set() -> None:
    config = RedisConfigLoader(redis_source_stub(REDIS_PASSWORD="s3cr3t")).load()

    assert config.worker_uri == "redis://:s3cr3t@localhost:6379/1"


def test_redis_names_the_acl_user_when_one_is_set() -> None:
    """Without the username the server applies `default`, which has +@all."""
    stub = redis_source_stub(REDIS_USER="app", REDIS_PASSWORD="s3cr3t")

    config = RedisConfigLoader(stub).load()

    assert config.worker_uri == "redis://app:s3cr3t@localhost:6379/1"


def test_redis_rejects_a_user_without_a_password() -> None:
    """An ACL user with no password silently degrades to an anonymous connect."""
    loader = RedisConfigLoader(redis_source_stub(REDIS_USER="app"))

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "REDIS_USER requires REDIS_PASSWORD" in render_exception(excinfo.value)


def test_redis_password_is_masked_in_error_output() -> None:
    stub = redis_source_stub(REDIS_PASSWORD="TOP-SECRET-VALUE", REDIS_PORT="999999")

    loader = RedisConfigLoader(stub)

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "TOP-SECRET-VALUE" not in render_exception(excinfo.value)


@pytest.mark.parametrize("db_index", ("-1", "16"))
def test_redis_rejects_a_database_index_outside_the_valid_range(db_index: str) -> None:
    loader = RedisConfigLoader(redis_source_stub(REDIS_WORKER_DB=db_index))

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "REDIS_WORKER_DB" in render_exception(excinfo.value)


def test_redis_rejects_two_purposes_sharing_a_database() -> None:
    """Silently sharing a database is the failure this catches at startup."""
    stub = redis_source_stub(REDIS_WORKER_DB="1", REDIS_SCHEDULE_SOURCE_DB="1")

    loader = RedisConfigLoader(stub)

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "different database indexes" in render_exception(excinfo.value)


def test_taskiq_loads_its_retry_policy() -> None:
    config = TaskIQConfigLoader(taskiq_source_stub()).load()

    assert config.default_retry_count == 3
    assert config.use_jitter
    assert config.use_delay_exponent


@pytest.mark.parametrize(
    ("variable", "value", "expected"),
    (
        ("TASKIQ_DEFAULT_RETRY_COUNT", "-1", "TASKIQ_DEFAULT_RETRY_COUNT"),
        ("TASKIQ_DEFAULT_DELAY", "-1", "TASKIQ_DEFAULT_DELAY"),
        ("TASKIQ_MAX_DELAY_EXPONENT", "0", "TASKIQ_MAX_DELAY_EXPONENT"),
        ("TASKIQ_RESULT_EX_TIME", "0", "TASKIQ_RESULT_EX_TIME"),
    ),
)
def test_taskiq_rejects_a_nonsensical_retry_policy(
    variable: str,
    value: str,
    expected: str,
) -> None:
    loader = TaskIQConfigLoader(taskiq_source_stub(**{variable: value}))

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert expected in render_exception(excinfo.value)


def test_mistral_requires_an_api_key() -> None:
    loader = MistralConfigLoader(mistral_source_stub(MISTRAL_API_KEY="   "))

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "MISTRAL_API_KEY must not be empty" in render_exception(excinfo.value)


def test_mistral_api_key_is_masked_in_error_output() -> None:
    """The key must never reach a log, and a startup failure is a log."""
    stub = mistral_source_stub(
        MISTRAL_API_KEY="sk-TOP-SECRET-VALUE",
        MISTRAL_TEMPERATURE="99",
    )

    loader = MistralConfigLoader(stub)

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "sk-TOP-SECRET-VALUE" not in render_exception(excinfo.value)


@pytest.mark.parametrize("temperature", ("-0.5", "2.5"))
def test_mistral_rejects_a_temperature_outside_the_valid_range(
    temperature: str,
) -> None:
    stub = mistral_source_stub(MISTRAL_TEMPERATURE=temperature)

    loader = MistralConfigLoader(stub)

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "MISTRAL_TEMPERATURE must be between" in render_exception(excinfo.value)


def test_mistral_rejects_a_non_positive_embedding_dimension() -> None:
    """The dimension is baked into the Qdrant collection; zero is unrecoverable."""
    stub = mistral_source_stub(MISTRAL_EMBEDDING_DIMENSION="0")

    loader = MistralConfigLoader(stub)

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "MISTRAL_EMBEDDING_DIMENSION must be positive" in render_exception(
        excinfo.value,
    )


def test_mistral_carries_default_request_timeouts() -> None:
    """A ceiling must exist even when nothing sets one.

    The SDK's own 120s default is far too long for a user waiting on a search or
    an answer.
    """
    config = MistralConfigLoader(mistral_source_stub()).load()

    assert config.embedding_timeout_seconds == 30
    assert config.chat_timeout_seconds == 60


@pytest.mark.parametrize(
    "variable",
    ("MISTRAL_EMBEDDING_TIMEOUT_SECONDS", "MISTRAL_CHAT_TIMEOUT_SECONDS"),
)
def test_mistral_rejects_a_non_positive_timeout(variable: str) -> None:
    """A zero timeout would mean 'give up before asking', which is not a ceiling."""
    loader = MistralConfigLoader(mistral_source_stub(**{variable: "0"}))

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert f"{variable} must be positive" in render_exception(excinfo.value)


def test_qdrant_builds_a_plain_http_url_by_default() -> None:
    config = QdrantConfigLoader(qdrant_source_stub()).load()

    assert config.url == "http://localhost:6333"


def test_qdrant_carries_a_default_request_timeout() -> None:
    config = QdrantConfigLoader(qdrant_source_stub()).load()

    assert config.timeout_seconds == 10


@pytest.mark.parametrize("value", ("0", "-3"))
def test_qdrant_rejects_a_non_positive_timeout(value: str) -> None:
    loader = QdrantConfigLoader(qdrant_source_stub(QDRANT_TIMEOUT_SECONDS=value))

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "QDRANT_TIMEOUT_SECONDS must be positive" in render_exception(excinfo.value)


def test_qdrant_switches_to_https_when_asked() -> None:
    config = QdrantConfigLoader(qdrant_source_stub(QDRANT_USE_HTTPS="true")).load()

    assert config.url == "https://localhost:6333"


def test_qdrant_requires_a_collection_name() -> None:
    stub = qdrant_source_stub(QDRANT_COLLECTION_NAME=" ")

    loader = QdrantConfigLoader(stub)

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "QDRANT_COLLECTION_NAME must not be empty" in render_exception(excinfo.value)


@pytest.mark.parametrize("port", ("0", "65536"))
def test_qdrant_rejects_a_port_outside_the_valid_range(port: str) -> None:
    loader = QdrantConfigLoader(qdrant_source_stub(QDRANT_PORT=port))

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "QDRANT_PORT must be between 1 and 65535" in render_exception(excinfo.value)


def test_qdrant_api_key_is_masked_in_error_output() -> None:
    stub = qdrant_source_stub(QDRANT_API_KEY="TOP-SECRET-VALUE", QDRANT_PORT="999999")

    loader = QdrantConfigLoader(stub)

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "TOP-SECRET-VALUE" not in render_exception(excinfo.value)


def test_storage_reads_the_upload_directory_as_a_path() -> None:
    config = StorageConfigLoader(
        storage_source_stub(SOURCE_STORAGE_DIRECTORY="/srv/uploads"),
    ).load()

    assert config.directory.name == "uploads"
