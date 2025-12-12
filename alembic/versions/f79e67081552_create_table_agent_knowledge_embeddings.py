"""Add embeddings table with HNSW index

Revision ID: f79e67081552
Revises: 913a4cd307d1
Create Date: 2025-08-31 01:09:53.824670
"""

from typing import Sequence, Union

import sqlalchemy as sa
from pgvector.sqlalchemy.vector import VECTOR

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f79e67081552"
down_revision: Union[str, Sequence[str], None] = "ff3d420cbce8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "agent_knowledge_embeddings"
SCHEMA_NAME = "agent"


def upgrade() -> None:
    """Upgrade schema."""
    # Garantir que a extensão vector exista
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Criar tabela embeddings
    op.create_table(
        TABLE_NAME,
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("application", sa.TEXT(), nullable=True),
        sa.Column("file_name", sa.TEXT(), nullable=True),
        sa.Column("content", sa.TEXT(), nullable=True),
        sa.Column("embedding", VECTOR(dim=1536), nullable=True),
        sa.Column("content_hash", sa.TEXT(), nullable=True),
        sa.UniqueConstraint(
            "content_hash", name="embeddings_content_hash_key"
        ),
        schema=SCHEMA_NAME,
    )

    # Criar índice HNSW para busca por similaridade
    op.create_index(
        "embeddings_embedding_idx",
        TABLE_NAME,
        ["embedding"],
        unique=False,
        schema=SCHEMA_NAME,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Dropar índice primeiro
    op.drop_index(
        "embeddings_embedding_idx", table_name=TABLE_NAME, schema=SCHEMA_NAME
    )

    # Dropar tabela
    op.drop_table(TABLE_NAME, schema=SCHEMA_NAME)
