from http import HTTPStatus

import pytest
from sqlalchemy import func, select
from voyageai.error import RateLimitError

from softsquat.models import Chunk, Document
from softsquat.routers import documents as documents_router
from softsquat.services import attach_service

URL = '/documents/'
LIMIT = 10


def upload(client, token, content, filename='manual.txt'):
    return client.post(
        URL,
        headers={'Authorization': f'Bearer {token}'},
        files={'file': (filename, content, 'text/plain')},
    )


async def count(session, model):
    return await session.scalar(select(func.count()).select_from(model))


@pytest.fixture
def small_limit(monkeypatch):
    monkeypatch.setattr(documents_router.settings, 'MAX_UPLOAD_BYTES', LIMIT)


@pytest.mark.asyncio
@pytest.mark.usefixtures('small_limit', 'fake_embeddings')
async def test_file_over_the_limit_is_rejected(client, token, session):
    response = upload(client, token, 'x' * (LIMIT + 1))

    assert response.status_code == HTTPStatus.CONTENT_TOO_LARGE
    assert await count(session, Document) == 0


@pytest.mark.asyncio
@pytest.mark.usefixtures('small_limit', 'fake_embeddings')
async def test_file_exactly_at_the_limit_is_accepted(client, token, session):
    response = upload(client, token, 'x' * LIMIT)

    assert response.status_code == HTTPStatus.CREATED
    assert await count(session, Document) == 1


@pytest.mark.asyncio
async def test_voyage_failure_returns_502_and_persists_nothing(
    client, token, session, monkeypatch
):
    async def failing_embed(_texts):
        raise RateLimitError('rate limit')

    monkeypatch.setattr(attach_service, 'embed_documents', failing_embed)

    response = upload(client, token, 'valid content')

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert await count(session, Document) == 0
    assert await count(session, Chunk) == 0
