from http import HTTPStatus

from softsquat.schemas import UserPublic


def test_create_user(client):
    response = client.post(
        '/users',
        json={
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'secret',
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == {
        'username': 'alice',
        'email': 'alice@example.com',
        'id': 1,
    }


def test_create_user_username_conflict(client, user):
    response = client.post(
        '/users',
        json={
            'username': user.username,
            'email': 'another_user@example.com',
            'password': 'anotherpassword',
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Username or Email already exists'}


def test_create_user_email_conflict(client, user):
    response = client.post(
        '/users',
        json={
            'username': 'another_user',
            'email': user.email,
            'password': 'anotherpassword',
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Username or Email already exists'}


def test_get_users(client):
    response = client.get('/users')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'users': []}


def test_read_users_with_users(client, user):
    user_schema = UserPublic.model_validate(user).model_dump()
    response = client.get('/users/')
    assert response.json() == {'users': [user_schema]}


def test_delete_user(client, user, token):
    user_id = user.id
    response = client.delete(
        f'/users/{user_id}', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'User deleted'}


# def test_delete_nonexistent_user(client):
#     response = client.delete('/users/999')
#     assert response.status_code == HTTPStatus.NOT_FOUND
#     assert response.json() == {'detail': 'User not found'}


def test_update_user(client, user, token):
    user_id = user.id
    response = client.put(
        f'/users/{user_id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': 'updated_user',
            'email': 'updated_user@example.com',
            'password': 'newpassword',
        },
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'id': user_id,
        'username': 'updated_user',
        'email': 'updated_user@example.com',
    }


def test_update_user_conflict_email(client, user, token):
    user_id = user.id
    client.post(
        '/users',
        json={
            'username': 'another_user',
            'email': 'another_user@example.com',
            'password': 'anotherpassword',
        },
    )
    response = client.put(
        f'/users/{user_id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': 'updated_user',
            'email': 'another_user@example.com',  # This email already exists
            'password': 'newpassword',
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Username or Email already exists'}


def test_update_user_conflict_username(client, user, token):
    user_id = user.id
    client.post(
        '/users',
        json={
            'username': 'another_user',
            'email': 'another_user@example.com',
            'password': 'anotherpassword',
        },
    )
    response = client.put(
        f'/users/{user_id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': 'another_user',
            'email': 'updated_user@example.com',
            'password': 'newpassword',
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Username or Email already exists'}


# def test_update_nonexistent_user(client):
#     response = client.put(
#         '/users/999',
#         json={
#             'username': 'nonexistent_user',
#             'email': 'nonexistent_user@example.com',
#             'password': 'nonexistentpassword',
#         },
#     )
#     assert response.status_code == HTTPStatus.UNAUTHORIZED
#     assert response.json() == {'detail': 'Could not validate credentials'}


def test_update_user_with_wrong_user(client, user, token):
    response = client.put(
        f'/users/{user.id + 1}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': 'bob',
            'email': 'bob@example.com',
            'password': 'mynewpassword',
        },
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {'detail': 'Not enough permissions'}


def test_delete_user_wrong_user(client, other_user, token):
    response = client.delete(
        f'/users/{other_user.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {'detail': 'Not enough permissions'}
