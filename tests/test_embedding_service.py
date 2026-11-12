from types import SimpleNamespace

import pytest

from softsquat.models import EMBED_DIM
from softsquat.services import embedding_service as svc
from softsquat.services.embedding_service import (
    RateLimiter,
    estimate_tokens,
    make_batches,
)

WINDOW = 60
TEXT_300 = 'a' * 300  # ~100 estimated tokens


class FakeTime:
    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self):
        return self.now

    async def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class FakeClient:
    def __init__(self):
        self.calls = []

    async def embed(self, texts, model, input_type, output_dimension):
        self.calls.append({
            'texts': list(texts),
            'model': model,
            'input_type': input_type,
            'output_dimension': output_dimension,
        })
        return SimpleNamespace(embeddings=[[float(len(text))] for text in texts])


class SpyLimiter:
    def __init__(self):
        self.acquired: list[int] = []

    async def acquire(self, tokens):
        self.acquired.append(tokens)


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(svc, '_client', client)
    return client


def limiter_with(fake_time, rpm=0, tpm=0):
    return RateLimiter(rpm, tpm, clock=fake_time.clock, sleep=fake_time.sleep)


# ---------------------------------------------------------------- batching


def test_estimate_tokens_is_at_least_one():
    assert estimate_tokens('') == 1
    assert estimate_tokens(TEXT_300) == len(TEXT_300) // 3


def test_batches_respect_max_items():
    texts = [TEXT_300] * 5

    batches = make_batches(texts, max_items=2, max_tokens=0)

    assert [len(batch) for batch in batches] == [2, 2, 1]


def test_batches_respect_token_budget():
    texts = [TEXT_300] * 5  # ~100 tokens each

    batches = make_batches(texts, max_items=64, max_tokens=250)

    assert [len(batch) for batch in batches] == [2, 2, 1]


def test_text_bigger_than_budget_goes_alone():
    batches = make_batches(['a' * 3000, 'b' * 30], max_items=64, max_tokens=100)

    assert [len(batch) for batch in batches] == [1, 1]


def test_no_texts_no_batches():
    assert make_batches([], max_items=64, max_tokens=0) == []


# ------------------------------------------------------------ rate limiter


@pytest.mark.asyncio
async def test_disabled_limiter_never_sleeps():
    fake = FakeTime()
    limiter = limiter_with(fake)

    for _ in range(100):
        await limiter.acquire(1_000_000)

    assert fake.sleeps == []


@pytest.mark.asyncio
async def test_rpm_limit_waits_for_the_window_to_expire():
    fake = FakeTime()
    limiter = limiter_with(fake, rpm=3)

    for _ in range(3):
        await limiter.acquire(1)
    assert fake.sleeps == []

    await limiter.acquire(1)

    assert fake.sleeps == [WINDOW]


@pytest.mark.asyncio
async def test_tpm_limit_waits_when_tokens_would_exceed_budget():
    fake = FakeTime()
    limiter = limiter_with(fake, tpm=100)

    await limiter.acquire(60)
    await limiter.acquire(30)
    assert fake.sleeps == []

    await limiter.acquire(30)  # 60 + 30 + 30 > 100

    assert fake.sleeps == [WINDOW]


@pytest.mark.asyncio
async def test_old_requests_leave_the_window():
    fake = FakeTime()
    limiter = limiter_with(fake, rpm=1)
    await limiter.acquire(1)

    fake.now += WINDOW + 1
    await limiter.acquire(1)

    assert fake.sleeps == []


@pytest.mark.asyncio
async def test_request_bigger_than_budget_does_not_block_forever():
    fake = FakeTime()
    limiter = limiter_with(fake, tpm=100)

    await limiter.acquire(500)  # empty window: the API decides

    assert fake.sleeps == []


# --------------------------------------------------------- embed functions


@pytest.mark.asyncio
async def test_embed_documents_batches_and_keeps_order(monkeypatch, fake_client):
    monkeypatch.setattr(svc.settings, 'EMBED_BATCH_SIZE', 2)
    monkeypatch.setattr(svc.settings, 'EMBED_TPM', 0)
    monkeypatch.setattr(svc, '_limiter', SpyLimiter())
    texts = ['a', 'bb', 'ccc', 'dddd', 'eeeee']

    vectors = await svc.embed_documents(texts)

    assert [len(call['texts']) for call in fake_client.calls] == [2, 2, 1]
    assert vectors == [[1.0], [2.0], [3.0], [4.0], [5.0]]
    assert all(call['input_type'] == 'document' for call in fake_client.calls)
    assert all(call['output_dimension'] == EMBED_DIM for call in fake_client.calls)
    assert all(call['model'] == svc.settings.EMBED_MODEL for call in fake_client.calls)


@pytest.mark.asyncio
async def test_embed_documents_acquires_budget_for_each_batch(monkeypatch, fake_client):
    spy = SpyLimiter()
    monkeypatch.setattr(svc.settings, 'EMBED_BATCH_SIZE', 2)
    monkeypatch.setattr(svc.settings, 'EMBED_TPM', 0)
    monkeypatch.setattr(svc, '_limiter', spy)

    await svc.embed_documents([TEXT_300] * 3)

    assert spy.acquired == [2 * estimate_tokens(TEXT_300), estimate_tokens(TEXT_300)]


@pytest.mark.asyncio
async def test_embed_documents_stays_within_free_trial_budget(monkeypatch, fake_client):
    fake = FakeTime()
    monkeypatch.setattr(svc.settings, 'EMBED_BATCH_SIZE', 64)
    monkeypatch.setattr(svc.settings, 'EMBED_TPM', 200)
    monkeypatch.setattr(svc, '_limiter', limiter_with(fake, rpm=3, tpm=200))

    await svc.embed_documents([TEXT_300] * 6)  # 6 x ~100 tokens, 200 per minute

    # each batch holds at most 2 texts and only one batch fits per minute
    assert [len(call['texts']) for call in fake_client.calls] == [2, 2, 2]
    assert fake.sleeps == [WINDOW, WINDOW]


@pytest.mark.asyncio
async def test_embed_query_uses_query_input_type(monkeypatch, fake_client):
    spy = SpyLimiter()
    monkeypatch.setattr(svc, '_limiter', spy)

    vector = await svc.embed_query('hello')

    assert vector == [5.0]
    assert fake_client.calls[0]['input_type'] == 'query'
    assert spy.acquired == [estimate_tokens('hello')]
