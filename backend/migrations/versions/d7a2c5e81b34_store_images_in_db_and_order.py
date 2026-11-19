"""store image bytes in the database; figure order inside a section

Revision ID: d7a2c5e81b34
Revises: c4f1a9e27d10
Create Date: 2026-11-19 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7a2c5e81b34'
down_revision: Union[str, Sequence[str], None] = 'c4f1a9e27d10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('reportimage', sa.Column('position', sa.Integer(), nullable=False, server_default='0'))
    op.create_table(
        'imageblob',
        sa.Column('image_id', sa.Integer(), nullable=False),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(['image_id'], ['reportimage.id']),
        sa.PrimaryKeyConstraint('image_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('imageblob')
    op.drop_column('reportimage', 'position')
