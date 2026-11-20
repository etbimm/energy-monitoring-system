"""legacy schema baseline

Revision ID: 20261120_legacy
Revises: 
Create Date: 2026-11-20 14:14:25.532456

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '20261120_legacy'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
