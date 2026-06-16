"""add kb_chunks table and vector extension

Revision ID: e7f8a9b0c1d2
Revises: d8b7e3c2a1f0
Create Date: 2026-06-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, Sequence[str], None] = 'd8b7e3c2a1f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        CREATE TABLE kb_chunks (
            id INTEGER NOT NULL,
            document_id VARCHAR NOT NULL,
            section VARCHAR NOT NULL,
            content TEXT NOT NULL,
            embedding vector(1536) NOT NULL,
            access_role VARCHAR NOT NULL,
            language VARCHAR NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (id)
        )
        """
    )

    op.execute(
        """
        CREATE INDEX ix_kb_chunks_embedding_hnsw
        ON kb_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_kb_chunks_embedding_hnsw")
    op.execute("DROP TABLE IF EXISTS kb_chunks")
    op.execute("DROP EXTENSION IF EXISTS vector")
