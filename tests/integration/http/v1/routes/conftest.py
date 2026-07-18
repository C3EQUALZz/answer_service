from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient, Response

type SourceFileUploader = Callable[..., Awaitable[Response]]

UPLOAD_URL = "/v1/indexing/upload"


@pytest.fixture()
def upload_source_file(client: AsyncClient) -> SourceFileUploader:
    """Posts a source file the way a client would."""

    async def upload(
        content: bytes,
        filename: str = "faq.csv",
        content_type: str = "text/csv",
    ) -> Response:
        return await client.post(
            UPLOAD_URL,
            files={"file": (filename, content, content_type)},
        )

    return upload
