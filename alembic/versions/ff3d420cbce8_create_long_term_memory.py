"""create_long_term_memory

Revision ID: ff3d420cbce8
Revises: f79e67081552
Create Date: 2025-11-02 22:32:36.108267

"""

from typing import Sequence, Union

import sqlalchemy as sa
from pgvector.sqlalchemy.vector import VECTOR

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ff3d420cbce8"
down_revision: Union[str, Sequence[str], None] = "ff5ac0a1173e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "long_term_memory"
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
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("agent_name", sa.Text(), nullable=True),
        sa.Column("role", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("embedding", VECTOR(dim=1536), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("usage_info", sa.JSON(), nullable=True),
        schema=SCHEMA_NAME,
    )

    # Criar índice HNSW para busca por similaridade
    op.create_index(
        "long_term_memory_embedding_idx",
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
        "long_term_memory_embedding_idx",
        table_name=TABLE_NAME,
        schema=SCHEMA_NAME,
    )

    # Dropar tabela
    op.drop_table(TABLE_NAME, schema=SCHEMA_NAME)
