from http import HTTPStatus

from softsquat.routers import chat as chat_router
from softsquat.schemas import ChatAnswer, ChatSource


def test_chat_ask_requires_authentication(client):
    response = client.post('/chat/ask', json={'message': 'How do I reset my password?'})

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_chat_ask_calls_rag_for_authenticated_user(client, token, user, monkeypatch):
    captured = {}

    async def fake_answer_question(*, session, user_id: int, question: str):
        captured['session'] = session
        captured['user_id'] = user_id
        captured['question'] = question
        return ChatAnswer(
            answer='Use account settings.',
            sources=[
                ChatSource(
                    document_id=42,
                    title='Account guide',
                    chunk_position=3,
                )
            ],
        )

    monkeypatch.setattr(chat_router, 'answer_question', fake_answer_question)

    response = client.post(
        '/chat/ask',
        headers={'Authorization': f'Bearer {token}'},
        json={'message': 'How do I reset my password?'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'answer': 'Use account settings.',
        'sources': [
            {
                'document_id': 42,
                'title': 'Account guide',
                'chunk_position': 3,
            }
        ],
    }
    assert captured['user_id'] == user.id
    assert captured['question'] == 'How do I reset my password?'
    assert captured['session'] is not None
