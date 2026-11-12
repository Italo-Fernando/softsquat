import pytest

from softsquat.models import EMBED_DIM, Chunk, Document
from softsquat.services import retrieval_service


@pytest.mark.asyncio
async def test_retrieve_orders_by_similarity_and_filters_other_users(
    session, user, other_user, monkeypatch
):
    query_vector = [1.0, 0.0] + [0.0] * (EMBED_DIM - 2)

    async def fake_embed_query(_query: str) -> list[float]:
        return query_vector

    monkeypatch.setattr(retrieval_service, 'embed_query', fake_embed_query)

    owned_document = Document(user_id=user.id, title='Owned')
    other_document = Document(user_id=other_user.id, title='Not owned')
    session.add_all([owned_document, other_document])
    await session.flush()

    session.add_all(
        [
            Chunk(
                document_id=owned_document.id,
                position=0,
                content='Less similar owned chunk',
                embedding=[0.0, 1.0] + [0.0] * (EMBED_DIM - 2),
            ),
            Chunk(
                document_id=owned_document.id,
                position=1,
                content='Most similar owned chunk',
                embedding=query_vector,
            ),
            Chunk(
                document_id=other_document.id,
                position=0,
                content='Exact match belonging to another user',
                embedding=query_vector,
            ),
        ]
    )
    await session.commit()

    results = await retrieval_service.retrieve_relevant_chunks(
        session=session,
        user_id=user.id,
        query='find the nearest passage',
    )

    assert [(chunk.content, title) for chunk, title in results] == [
        ('Most similar owned chunk', 'Owned'),
        ('Less similar owned chunk', 'Owned'),
    ]
