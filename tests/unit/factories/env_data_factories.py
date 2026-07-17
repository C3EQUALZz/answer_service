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
