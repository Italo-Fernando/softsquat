from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from softsquat.database import get_session
from softsquat.models import User
from softsquat.schemas import ChatAnswer, ChatRequest
from softsquat.security import get_current_user
from softsquat.services.rag_service import answer_question

router = APIRouter(prefix='/chat', tags=['chat'])
CurrentUser = Annotated[User, Depends(get_current_user)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post('/ask', status_code=HTTPStatus.OK, response_model=ChatAnswer)
async def ask_question(request: ChatRequest, user: CurrentUser, session: SessionDep):
    return await answer_question(
        session=session,
        user_id=user.id,
        question=request.message,
    )
