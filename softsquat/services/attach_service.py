from softsquat.models import Chunk, Document
from softsquat.services.embedding_service import embed_documents

# Preferred break points, best first: paragraph, line, sentence, word.
_BREAKS = ('\n\n', '\n', '. ', '! ', '? ', ' ')


def _find_end(text: str, start: int, hard_end: int, min_end: int) -> int:
    """Last natural break in [min_end, hard_end]; hard_end if there is none."""
    window = text[start:hard_end]
    for separator in _BREAKS:
        index = window.rfind(separator, min_end - start)
        if index != -1:
            return start + index + len(separator)
    return hard_end


def _skip_to_word_start(text: str, pos: int, limit: int) -> int:
    """If `pos` falls inside a word, move to the start of the next word."""
    if pos == 0 or text[pos - 1].isspace():
        return pos
    for index in range(pos, limit):
        if text[index].isspace():
            return index + 1
    return pos


def chunk_text(text: str, size: int = 800, overlap: int = 150) -> list[str]:
    """Split `text` into chunks of at most `size` chars without cutting words.

    Chunks end at a paragraph, line, sentence or word boundary, looking only in
    the second half of the window. With no whitespace at all (one giant token)
    it falls back to a hard cut at `size`. Consecutive chunks share about
    `overlap` chars and always start at the beginning of a word.
    """
    if overlap >= size:
        raise ValueError('overlap must be smaller than size')

    chunks: list[str] = []
    start, total = 0, len(text)
    while start < total:
        hard_end = min(start + size, total)
        if hard_end == total:
            end = total
        else:
            end = _find_end(text, start, hard_end, start + size // 2)

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= total:
            break
        start = _skip_to_word_start(text, max(end - overlap, start + 1), end)
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
