from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from softsquat.models import Chunk, Document
from softsquat.services.embedding_service import embed_query


async def retrieve_relevant_chunks(
    session: AsyncSession,
    user_id: int,
    query: str,
    limit: int = 5,
) -> list[tuple[Chunk, str]]:
    if not query.strip():
        raise ValueError('query must not be empty')
    if limit < 1:
        raise ValueError('limit must be greater than zero')

    query_embedding = await embed_query(query)
    distance = Chunk.embedding.cosine_distance(query_embedding)
    statement = (
        select(Chunk, Document.title)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.user_id == user_id)
        .order_by(distance)
        .limit(limit)
    )
    result = await session.execute(statement)
    return list(result.all())
