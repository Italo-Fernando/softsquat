import asyncio
import time
from collections import deque
from collections.abc import Callable

import voyageai

from softsquat.models import EMBED_DIM
from softsquat.settings import Settings

settings = Settings()

_client = voyageai.AsyncClient(api_key=settings.VOYAGE_KEY, max_retries=3, timeout=30)

WINDOW_SECONDS = 60


def estimate_tokens(text: str) -> int:
    """Conservative estimate (~3 chars per token) used to plan batches."""
    return max(1, len(text) // 3)


class RateLimiter:
    """Sliding 60s window enforcing requests-per-minute and tokens-per-minute.

    An `rpm` or `tpm` of 0 disables that dimension.
    """

    def __init__(
        self,
        rpm: int = 0,
        tpm: int = 0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], object] = asyncio.sleep,
    ):
        self.rpm = rpm
        self.tpm = tpm
        self._clock = clock
        self._sleep = sleep
        self._events: deque[tuple[float, int]] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int) -> None:
        if not (self.rpm or self.tpm):
            return
        async with self._lock:
            while True:
                now = self._clock()
                while self._events and now - self._events[0][0] >= WINDOW_SECONDS:
                    self._events.popleft()

                used = sum(count for _, count in self._events)
                fits_rpm = not self.rpm or len(self._events) < self.rpm
                fits_tpm = not self.tpm or used + tokens <= self.tpm
                # empty window: let it through and let the API decide, so a
                # request bigger than the budget cannot block forever
                if not self._events or (fits_rpm and fits_tpm):
                    self._events.append((now, tokens))
                    return

                wait = WINDOW_SECONDS - (now - self._events[0][0])
                await self._sleep(max(wait, 0.05))


_limiter = RateLimiter(settings.EMBED_RPM, settings.EMBED_TPM)


def make_batches(texts: list[str], max_items: int, max_tokens: int) -> list[list[str]]:
    """Group texts into batches bounded by item count and estimated tokens.

    A `max_tokens` of 0 disables the token bound. A text that alone exceeds the
    bound is sent in a batch of its own.
    """
    batches: list[list[str]] = []
    current: list[str] = []
    current_tokens = 0
    for text in texts:
        tokens = estimate_tokens(text)
        too_many = len(current) >= max_items
        too_big = max_tokens and current and current_tokens + tokens > max_tokens
        if current and (too_many or too_big):
            batches.append(current)
            current, current_tokens = [], 0
        current.append(text)
        current_tokens += tokens
    if current:
        batches.append(current)
    return batches


async def embed_documents(texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []

    for batch in make_batches(texts, settings.EMBED_BATCH_SIZE, settings.EMBED_TPM):
        await _limiter.acquire(sum(estimate_tokens(text) for text in batch))
        result = await _client.embed(
            batch,
            model=settings.EMBED_MODEL,
            input_type='document',
            output_dimension=EMBED_DIM,
        )
        vectors.extend(result.embeddings)
    return vectors


async def embed_query(text: str) -> list[float]:
    await _limiter.acquire(estimate_tokens(text))
    result = await _client.embed(
        [text],
        model=settings.EMBED_MODEL,
        input_type='query',
        output_dimension=EMBED_DIM,
    )
    return result.embeddings[0]
