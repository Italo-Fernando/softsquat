import voyageai

from softsquat.models import EMBED_DIM
from softsquat.settings import Settings

BATCH_SIZE = 64

settings = Settings()

_client = voyageai.AsyncClient(api_key=settings.VOYAGE_KEY, max_retries=3, timeout=30)


async def embed_documents(texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        result = await _client.embed(
            texts[i : i + BATCH_SIZE],
            model=settings.EMBED_MODEL,
            input_type='document',
            output_dimension=EMBED_DIM,
        )
        vectors.extend(result.embeddings)
    return vectors


async def embed_query(text: str) -> list[float]:
    result = await _client.embed(
        [text],
        model=settings.EMBED_MODEL,
        input_type='query',
        output_dimension=EMBED_DIM,
    )
    return result.embeddings[0]
