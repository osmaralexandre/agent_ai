"""create_db

Revision ID: ff5ac0a1173e
Revises:
Create Date: 2025-08-30 18:23:31.412484

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ff5ac0a1173e"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS agent")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS agent CASCADE")
