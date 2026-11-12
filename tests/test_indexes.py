import pytest
from sqlalchemy import text

QUERY = "SELECT indexname FROM pg_indexes WHERE tablename IN ('documents', 'chunks')"


@pytest.mark.asyncio
async def test_filter_columns_are_indexed(session):
    result = await session.execute(text(QUERY))

    names = {row[0] for row in result}

    assert {'ix_documents_user_id', 'ix_chunks_document_id'} <= names
