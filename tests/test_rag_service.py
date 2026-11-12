from types import SimpleNamespace

import pytest

from softsquat.models import Chunk
from softsquat.schemas import ChatAnswer, ChatSource
from softsquat.services import rag_service

TEST_USER_ID = 7


@pytest.mark.asyncio
async def test_answer_question_sends_retrieved_context_and_returns_sources(
    session, monkeypatch
):
    chunk = Chunk(
        document_id=42,
        position=3,
        content='Reset the password from account settings.',
        embedding=[1.0] + [0.0] * 1023,
    )
    retrieved = [(chunk, 'Account guide')]
    captured = {}

    async def fake_retrieve_relevant_chunks(**kwargs):
        assert kwargs['session'] is session
        assert kwargs['user_id'] == TEST_USER_ID
        assert kwargs['query'] == 'How do I reset my password?'
        return retrieved

    class FakeLLM:
        @staticmethod
        async def ainvoke(messages):
            captured['messages'] = messages
            return SimpleNamespace(content='Use the account settings.')

    monkeypatch.setattr(
        rag_service, 'retrieve_relevant_chunks', fake_retrieve_relevant_chunks
    )
    monkeypatch.setattr(rag_service, 'llm', FakeLLM())

    answer = await rag_service.answer_question(
        session=session,
        user_id=TEST_USER_ID,
        question='How do I reset my password?',
    )

    prompt = '\n'.join(str(message.content) for message in captured['messages'])
    assert 'Account guide' in prompt
    assert 'Reset the password from account settings.' in prompt
    assert 'How do I reset my password?' in prompt
    assert answer == ChatAnswer(
        answer='Use the account settings.',
        sources=[
            ChatSource(document_id=42, title='Account guide', chunk_position=3)
        ],
    )
