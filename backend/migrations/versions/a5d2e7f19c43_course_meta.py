"""course projects: report.meta (task sheet, calendar plan, abbreviations, ...)

Revision ID: a5d2e7f19c43
Revises: f3c8a1d5e902
Create Date: 2026-11-28 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5d2e7f19c43'
down_revision: Union[str, Sequence[str], None] = 'f3c8a1d5e902'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('report', sa.Column('meta', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('report', 'meta')
