"""concurrent test

Revision ID: f83091257b57
Revises: b58746ce2d5d
Create Date: 2025-10-15 18:08:07.338767

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f83091257b57'
down_revision: Union[str, Sequence[str], None] = 'b58746ce2d5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
