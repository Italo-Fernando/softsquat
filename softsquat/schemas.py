from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Message(BaseModel):
    message: str


class UserSchema(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: int
    username: str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)


class UserDB:
    id: int


class UserList(BaseModel):
    users: list[UserPublic]


class Token(BaseModel):
    access_token: str
    token_type: str


class FilterPage(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

class ChatSource(BaseModel):
    document_id: int
    title: str
    chunk_position: int

class ChatAnswer(BaseModel):
    answer: str
    sources: list[ChatSource]