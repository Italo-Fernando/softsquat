from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from softsquat.models import User
from softsquat.schemas import SupportRequest, SupportResponse, UserPublic
from softsquat.security import get_current_user

router = APIRouter(prefix='/chat', tags=['chat'])
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post('/classify', status_code=HTTPStatus.OK, response_model=SupportResponse)
async def classify_message(request: SupportRequest, user: CurrentUser):
    ...
