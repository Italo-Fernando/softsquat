from http import HTTPStatus
from types import SimpleNamespace

import pytest

from softsquat.models import EMBED_DIM, Chunk, Document
from softsquat.services import rag_service, retrieval_service

NOT_FOUND = 'Não encontrei informações relevantes nos seus documentos.'
MAX_DISTANCE = 0.5


def vector(*head: float) -> list[float]:
    return [*head] + [0.0] * (EMBED_DIM - len(head))


async def seed_chunks(session, user, vectors):
    document = Document(user_id=user.id, title='Doc')
    session.add(document)
    await session.flush()
    session.add_all(
        Chunk(document_id=document.id, position=i, content=f'chunk {i}', embedding=v)
        for i, v in enumerate(vectors)
    )
    await session.commit()


@pytest.fixture
def query_is_x_axis(monkeypatch):
    async def fake_embed_query(_query):
        return vector(1.0)

    monkeypatch.setattr(retrieval_service, 'embed_query', fake_embed_query)


async def retrieve(session, user, **kwargs):
    results = await retrieval_service.retrieve_relevant_chunks(
        session=session, user_id=user.id, query='anything', **kwargs
    )
    return [chunk.content for chunk, _ in results]


@pytest.mark.asyncio
async def test_max_distance_drops_unrelated_chunks(session, user, query_is_x_axis):
    # distances to the query: 0.0, 0.2 and 1.0
    await seed_chunks(session, user, [vector(1.0), vector(0.8, 0.6), vector(0.0, 1.0)])

    assert await retrieve(session, user, max_distance=MAX_DISTANCE) == [
        'chunk 0',
        'chunk 1',
    ]


@pytest.mark.asyncio
async def test_tighter_max_distance_keeps_only_the_closest(
    session, user, query_is_x_axis
):
    await seed_chunks(session, user, [vector(1.0), vector(0.8, 0.6), vector(0.0, 1.0)])

    assert await retrieve(session, user, max_distance=0.1) == ['chunk 0']


@pytest.mark.asyncio
async def test_without_max_distance_nothing_is_filtered(session, user, query_is_x_axis):
    await seed_chunks(session, user, [vector(1.0), vector(0.8, 0.6), vector(0.0, 1.0)])

    assert await retrieve(session, user) == ['chunk 0', 'chunk 1', 'chunk 2']


@pytest.mark.asyncio
async def test_returns_empty_when_everything_is_too_far(session, user, query_is_x_axis):
    await seed_chunks(session, user, [vector(0.0, 1.0), vector(0.0, 0.0, 1.0)])

    assert await retrieve(session, user, max_distance=MAX_DISTANCE) == []


@pytest.mark.asyncio
async def test_rag_passes_configured_max_distance_to_retrieval(session, monkeypatch):
    captured = {}

    async def fake_retrieve(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(rag_service, 'retrieve_relevant_chunks', fake_retrieve)
    monkeypatch.setattr(rag_service.settings, 'RETRIEVAL_MAX_DISTANCE', 0.42)

    await rag_service.answer_question(session=session, user_id=1, question='?')

    assert captured['max_distance'] == pytest.approx(0.42)


@pytest.mark.asyncio
async def test_rag_does_not_call_llm_when_nothing_is_relevant(session, monkeypatch):
    class ExplodingLLM:
        @staticmethod
        async def ainvoke(_messages):
            raise AssertionError('the LLM must not be called without context')

    async def fake_retrieve(**_kwargs):
        return []

    monkeypatch.setattr(rag_service, 'retrieve_relevant_chunks', fake_retrieve)
    monkeypatch.setattr(rag_service, 'llm', ExplodingLLM())

    answer = await rag_service.answer_question(session=session, user_id=1, question='?')

    assert answer.answer == NOT_FOUND
    assert answer.sources == []


@pytest.mark.asyncio
@pytest.mark.usefixtures('query_is_x_axis')
async def test_chat_ask_says_not_found_for_unrelated_question(
    client, token, user, session, monkeypatch
):
    await seed_chunks(session, user, [vector(0.0, 1.0)])  # unrelated to the query

    class ExplodingLLM:
        @staticmethod
        async def ainvoke(_messages):
            raise AssertionError('the LLM must not be called without context')

    monkeypatch.setattr(rag_service, 'llm', ExplodingLLM())
    monkeypatch.setattr(rag_service.settings, 'RETRIEVAL_MAX_DISTANCE', MAX_DISTANCE)

    response = client.post(
        '/chat/ask',
        headers={'Authorization': f'Bearer {token}'},
        json={'message': 'something unrelated'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'answer': NOT_FOUND, 'sources': []}


@pytest.mark.asyncio
@pytest.mark.usefixtures('query_is_x_axis')
async def test_chat_ask_uses_close_chunk_and_calls_llm(
    client, token, user, session, monkeypatch
):
    await seed_chunks(session, user, [vector(0.9, 0.1), vector(0.0, 1.0)])

    class FakeLLM:
        @staticmethod
        async def ainvoke(_messages):
            return SimpleNamespace(content='resposta')

    monkeypatch.setattr(rag_service, 'llm', FakeLLM())
    monkeypatch.setattr(rag_service.settings, 'RETRIEVAL_MAX_DISTANCE', MAX_DISTANCE)

    response = client.post(
        '/chat/ask',
        headers={'Authorization': f'Bearer {token}'},
        json={'message': 'related question'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['answer'] == 'resposta'
    assert [s['chunk_position'] for s in response.json()['sources']] == [0]
