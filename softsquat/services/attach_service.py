from softsquat.models import Chunk, Document
from softsquat.services.embedding_service import embed_documents


def chunk_text(text: str, size: int = 800, overlap: int = 150) -> list[str]:
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return chunks


async def ingest(session, user_id: int, title: str, text: str) -> Document:
    chunks = chunk_text(text)
    vectors = await embed_documents(chunks)

    doc = Document(user_id=user_id, title=title)
    session.add(doc)
    await session.flush()  # gera doc.id

    session.add_all(
        Chunk(document_id=doc.id, position=i, content=c, embedding=v)
        for i, (c, v) in enumerate(zip(chunks, vectors))
    )
    await session.commit()
    return doc
