"""add generated questions table

Revision ID: e0fcf505ff94
Revises: e9d63d880d9c
Create Date: 2026-07-22 01:36:28.261312

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0fcf505ff94'
down_revision: Union[str, Sequence[str], None] = 'e9d63d880d9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
