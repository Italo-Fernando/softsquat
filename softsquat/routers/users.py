from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from softsquat.database import get_session
from softsquat.models import User
from softsquat.schemas import UserPublic, UserSchema

router = APIRouter(prefix='/users', tags=['users'])


@router.post('/', status_code=HTTPStatus.CREATED, response_model=UserPublic)
def create_user(user: UserSchema, session: Annotated[Session, Depends(get_session)]):
    db_user = session.scalar(
        select(User).where((User.username == user.username) | (User.email == user.email))
    )

    if db_user:
        if db_user.username == user.username:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Username already exists',
            )
        elif db_user.email == user.email:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Email already exists',
            )

    db_user = User(
        email=user.email,
        username=user.username,
        password=user.password,
    )

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user


@router.get('/{user_id}', response_model=UserPublic, status_code=HTTPStatus.ACCEPTED)
def get_user(user_id: int, session: Annotated[Session, Depends(get_session)]):
    db_user = session.get(User, user_id)
    if db_user is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='User not found',
        )

    return {'username': db_user.username, 'email': db_user.email}


@router.put('/{user_id}', response_model=UserPublic, status_code=HTTPStatus.OK)
def update_user(
    user_id: int,
    user: UserSchema,
    session: Annotated[Session, Depends(get_session)],
):
    db_user = session.get(User, user_id)
    if db_user is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='User not found',
        )

    conflicting_user = session.scalar(
        select(User).where(
            ((User.username == user.username) | (User.email == user.email))
            & (User.id != user_id)
        )
    )
    if conflicting_user:
        if conflicting_user.username == user.username:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Username already exists',
            )
        if conflicting_user.email == user.email:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Email already exists',
            )

    db_user.username = user.username
    db_user.email = user.email
    db_user.password = user.password
    session.commit()
    session.refresh(db_user)

    return {'username': db_user.username, 'email': db_user.email}


@router.delete('/{user_id}', status_code=HTTPStatus.NO_CONTENT)
def delete_user(user_id: int, session: Annotated[Session, Depends(get_session)]):
    db_user = session.get(User, user_id)
    if db_user is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='User not found',
        )

    session.delete(db_user)
    session.commit()
