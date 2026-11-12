"""add btree indexes on filter columns

Revision ID: b7c1d2e3f4a5
Revises: ef28bca98f70
Create Date: 2026-11-12 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7c1d2e3f4a5'
down_revision: Union[str, Sequence[str], None] = 'ef28bca98f70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'])
    op.create_index(op.f('ix_chunks_document_id'), 'chunks', ['document_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_chunks_document_id'), table_name='chunks')
    op.drop_index(op.f('ix_documents_user_id'), table_name='documents')
