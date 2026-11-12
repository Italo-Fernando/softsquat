
from typing import Annotated

from fastapi import APIRouter, HTTPException
from http import HTTPStatus

from softsquat.services.attach_service import ingest

from softsquat.models import User
from fastapi import UploadFile, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from softsquat.database import get_session
from softsquat.security import get_current_user


router = APIRouter(prefix='/documents', tags=['documents'])
CurrentUser = Annotated[User, Depends(get_current_user)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]

@router.post('/', status_code=HTTPStatus.CREATED)
async def upload_document(file: UploadFile, user: CurrentUser, session: SessionDep):
    try:
        text = (await file.read()).decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, 'Envie um arquivo de texto UTF-8')
    if not text.strip():
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, 'Arquivo vazio')
    doc = await ingest(session, user.id, file.filename or 'sem título', text)
    return {'id': doc.id, 'title': doc.title}