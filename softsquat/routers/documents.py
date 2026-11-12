from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from softsquat.database import get_session
from softsquat.models import Document, User
from softsquat.schemas import Message
from softsquat.security import get_current_user
from softsquat.services.attach_service import ingest

router = APIRouter(prefix='/documents', tags=['documents'])
CurrentUser = Annotated[User, Depends(get_current_user)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post('/', status_code=HTTPStatus.CREATED)
async def upload_document(file: UploadFile, user: CurrentUser, session: SessionDep):
    try:
        text = (await file.read()).decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            HTTPStatus.UNPROCESSABLE_ENTITY, 'Envie um arquivo de texto UTF-8'
        )
    if not text.strip():
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, 'Arquivo vazio')
    doc = await ingest(session, user.id, file.filename or 'sem título', text)
    return {'id': doc.id, 'title': doc.title}


@router.delete(
    '/{document_id}',
    status_code=HTTPStatus.OK,
    response_model=Message,
)
async def delete_document(
    document_id: int,
    user: CurrentUser,
    session: SessionDep,
):
    document = await session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user.id,
        )
    )
    if document is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found',
        )

    await session.delete(document)
    await session.commit()
    return {'message': 'Document deleted'}
