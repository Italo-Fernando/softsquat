import pytest
from sqlalchemy import select

from softsquat.models import EMBED_DIM, Chunk
from softsquat.services.attach_service import ingest


@pytest.mark.asyncio
async def test_ingest_persists_document_chunks_and_embeddings(
    session, user, fake_embeddings
):
    text = 'a' * 900

    document = await ingest(
        session=session,
        user_id=user.id,
        title='Support guide',
        text=text,
    )

    chunks = await session.scalars(
        select(Chunk)
        .where(Chunk.document_id == document.id)
        .order_by(Chunk.position)
    )
    chunks = list(chunks.all())

    assert document.title == 'Support guide'
    assert document.user_id == user.id
    assert [chunk.position for chunk in chunks] == [0, 1]
    assert [len(chunk.content) for chunk in chunks] == [800, 250]
    assert all(len(chunk.embedding) == EMBED_DIM for chunk in chunks)
