from http import HTTPStatus
from typing import Annotated

from email_validator import EmailNotValidError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from softsquat.database import get_session
from softsquat.models import User
from softsquat.schemas import FilterPage, Message, UserList, UserPublic, UserSchema
from softsquat.security import get_current_user, get_password_hash
from softsquat.services.email_service import check_email

router = APIRouter(prefix='/users', tags=['users'])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post('/', status_code=HTTPStatus.CREATED, response_model=UserPublic)
async def create_user(user: UserSchema, session: SessionDep):
    try:
        user.email = check_email(user.email)
    except EmailNotValidError:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail='Email is not valid'
        )

    db_user = await session.scalar(
        select(User).where((User.username == user.username) | (User.email == user.email))
    )

    if db_user:
        if db_user.username == user.username:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Username or Email already exists',
            )
        elif db_user.email == user.email:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Username or Email already exists',
            )

    hased_password = get_password_hash(user.password)

    db_user = User(
        email=user.email,
        username=user.username,
        password=hased_password,
    )

    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    return db_user


@router.get('/', response_model=UserList, status_code=HTTPStatus.OK)
async def get_users(session: SessionDep, filter_users: Annotated[FilterPage, Depends()]):
    result = await session.scalars(
        select(User).offset(filter_users.offset).limit(filter_users.limit)
    )
    users = result.all()
    return {'users': users}


@router.get('/{user_id}', response_model=UserPublic, status_code=HTTPStatus.ACCEPTED)
async def get_user(user_id: int, session: SessionDep):
    db_user = await session.get(User, user_id)
    if db_user is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='User not found',
        )

    return {'username': db_user.username, 'email': db_user.email}


@router.put('/{user_id}', response_model=UserPublic, status_code=HTTPStatus.OK)
async def update_user(
    user_id: int,
    user: UserSchema,
    session: SessionDep,
    current_user: CurrentUser,
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Not enough permissions',
        )

    try:
        current_user.username = user.username
        current_user.password = get_password_hash(user.password)
        current_user.email = user.email
        await session.commit()
        await session.refresh(current_user)
        return current_user

    except IntegrityError:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail='Username or Email already exists'
        )


@router.delete('/{user_id}', status_code=HTTPStatus.OK, response_model=Message)
async def delete_user(
    user_id: int,
    session: SessionDep,
    current_user: CurrentUser,
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Not enough permissions',
        )
    await session.delete(current_user)
    await session.commit()

    return {'message': 'User deleted'}
