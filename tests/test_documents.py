from http import HTTPStatus

import pytest
from sqlalchemy import func, select

from softsquat.models import EMBED_DIM, Chunk, Document


@pytest.mark.asyncio
async def test_delete_document_deletes_its_chunks(client, session, user, token):
    document = Document(user_id=user.id, title='Support guide')
    session.add(document)
    await session.flush()
    session.add(
        Chunk(
            document_id=document.id,
            content='Document content',
            embedding=[1.0] + [0.0] * (EMBED_DIM - 1),
            position=0,
        )
    )
    await session.commit()

    response = client.delete(
        f'/documents/{document.id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Document deleted'}
    assert await session.get(Document, document.id) is None
    remaining_chunks = await session.scalar(select(func.count()).select_from(Chunk))
    assert remaining_chunks == 0


@pytest.mark.asyncio
async def test_delete_document_does_not_delete_another_users_document(
    client, session, user, token, other_user
):
    document = Document(user_id=other_user.id, title='Private guide')
    session.add(document)
    await session.commit()

    response = client.delete(
        f'/documents/{document.id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Document not found'}
    assert await session.get(Document, document.id) is not None


def test_delete_document_requires_authentication(client):
    response = client.delete('/documents/1')

    assert response.status_code == HTTPStatus.UNAUTHORIZED
