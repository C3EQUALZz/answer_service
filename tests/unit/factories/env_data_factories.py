def postgres_env(**overrides: str) -> dict[str, str]:
    """Valid ``POSTGRES_*`` env values (name -> value); override any key."""
    data = {
        "POSTGRES_USER": "app",
        "POSTGRES_PASSWORD": "s3cr3t",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "app_db",
        "POSTGRES_DRIVER": "asyncpg",
    }
    data.update(overrides)
    return data


def sqlalchemy_env(**overrides: str) -> dict[str, str]:
    """Valid ``DB_*`` env values (name -> value); override any key.

    Only the required fields are provided; optional fields (auto_flush,
    expire_on_commit, future) fall back to their dataclass defaults.
    """
    data = {
        "DB_POOL_PRE_PING": "true",
        "DB_POOL_RECYCLE": "30",
        "DB_POOL_SIZE": "10",
        "DB_POOL_MAX_OVERFLOW": "5",
        "DB_ECHO": "false",
    }
    data.update(overrides)
    return data


def asgi_env(**overrides: str) -> dict[str, str]:
    """Valid ``UVICORN_*`` / ``FASTAPI_*`` env values; override any key."""
    data = {
        "UVICORN_HOST": "127.0.0.1",
        "UVICORN_PORT": "8080",
        "FASTAPI_DEBUG": "true",
        "FASTAPI_ALLOW_CREDENTIALS": "false",
    }
    data.update(overrides)
    return data


def logging_env(**overrides: str) -> dict[str, str]:
    """Valid logging env values (name -> value); override any key."""
    data = {
        "RENDER_JSON_LOGS": "true",
        "PATH_TO_SAVE_LOGS": "/var/log/app",
        "LOG_LEVEL": "DEBUG",
    }
    data.update(overrides)
    return data


def nats_env(**overrides: str) -> dict[str, str]:
    """Valid ``NATS_*`` values; override any key."""
    return {
        "NATS_HOST": "localhost",
        "NATS_PORT": "4222",
        "NATS_USER": "",
        "NATS_PASSWORD": "",
    } | overrides


def redis_env(**overrides: str) -> dict[str, str]:
    """Valid ``REDIS_*`` values; override any key."""
    return {
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_USER": "",
        "REDIS_PASSWORD": "",
        "REDIS_WORKER_DB": "1",
        "REDIS_SCHEDULE_SOURCE_DB": "2",
        "REDIS_CACHE_DB": "0",
    } | overrides


def taskiq_env(**overrides: str) -> dict[str, str]:
    """Valid ``TASKIQ_*`` values; override any key."""
    return {
        "TASKIQ_SUBJECT": "answer_service.tasks",
        "TASKIQ_STREAM_NAME": "answer_service_jetstream",
        "TASKIQ_DURABLE": "answer_service_durable",
        "TASKIQ_QUEUE": "answer_service_workers",
        "TASKIQ_RESULT_EX_TIME": "1000",
        "TASKIQ_DEFAULT_RETRY_COUNT": "3",
        "TASKIQ_DEFAULT_DELAY": "5.0",
        "TASKIQ_USE_JITTER": "true",
        "TASKIQ_USE_DELAY_EXPONENT": "true",
        "TASKIQ_MAX_DELAY_EXPONENT": "60.0",
    } | overrides


def mistral_env(**overrides: str) -> dict[str, str]:
    """Valid ``MISTRAL_*`` values; override any key."""
    return {
        "MISTRAL_API_KEY": "test-api-key",
        "MISTRAL_BASE_URL": "",
        "MISTRAL_EMBEDDING_MODEL": "mistral-embed",
        "MISTRAL_EMBEDDING_DIMENSION": "1024",
        "MISTRAL_CHAT_MODEL": "mistral-large-latest",
        "MISTRAL_TEMPERATURE": "0.0",
        "MISTRAL_MAX_CONCURRENCY": "5",
        "MISTRAL_EMBEDDING_TIMEOUT_SECONDS": "30",
        "MISTRAL_CHAT_TIMEOUT_SECONDS": "60",
    } | overrides


def qdrant_env(**overrides: str) -> dict[str, str]:
    """Valid ``QDRANT_*`` values; override any key."""
    return {
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "6333",
        "QDRANT_API_KEY": "",
        "QDRANT_COLLECTION_NAME": "qa_pairs",
        "QDRANT_USE_HTTPS": "false",
        "QDRANT_PREFER_GRPC": "false",
        "QDRANT_TIMEOUT_SECONDS": "10",
    } | overrides


def storage_env(**overrides: str) -> dict[str, str]:
    """Valid ``SOURCE_STORAGE_*`` values; override any key."""
    return {"SOURCE_STORAGE_DIRECTORY": "var/uploads"} | overrides
