import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from softsquat.models import Chunk, Document
from softsquat.services.embedding_service import embed_query

# uvicorn's logger is already configured, so these lines show up in the console
logger = logging.getLogger('uvicorn.error')


async def retrieve_relevant_chunks(
    session: AsyncSession,
    user_id: int,
    query: str,
    limit: int = 5,
    max_distance: float | None = None,
) -> list[tuple[Chunk, str]]:
    """Closest chunks of the user's documents to the query.

    When `max_distance` is given, chunks with a larger cosine distance are
    dropped (0 = identical, 1 = unrelated, 2 = opposite).
    """
    if not query.strip():
        raise ValueError('query must not be empty')
    if limit < 1:
        raise ValueError('limit must be greater than zero')

    query_embedding = await embed_query(query)
    distance = Chunk.embedding.cosine_distance(query_embedding)
    statement = (
        select(Chunk, Document.title, distance.label('distance'))
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.user_id == user_id)
    )
    if max_distance is not None:
        statement = statement.where(distance <= max_distance)

    result = await session.execute(statement.order_by(distance).limit(limit))
    rows = result.all()

    logger.info(
        'retrieval: %d chunks (max_distance=%s) distances=%s',
        len(rows),
        max_distance,
        [round(float(row.distance), 3) for row in rows],
    )
    return [(chunk, title) for chunk, title, _ in rows]
