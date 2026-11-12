from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_as_dataclass, mapped_column, registry

table_registry = registry()
EMBED_DIM = 1024


@mapped_as_dataclass(table_registry)
class User:
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(init=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )


@mapped_as_dataclass(table_registry)
class Document:
    __tablename__ = 'documents'
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    title: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(init=False, server_default=func.now())


@mapped_as_dataclass(table_registry)
class Chunk:
    __tablename__ = 'chunks'
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey('documents.id', ondelete='CASCADE')
    )
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM))
    position: Mapped[int]
