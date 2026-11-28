"""built .docx / .pdf files are stored in the database (several server instances)

Revision ID: b8e4c2a7d951
Revises: a5d2e7f19c43
Create Date: 2026-11-28 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8e4c2a7d951'
down_revision: Union[str, Sequence[str], None] = 'a5d2e7f19c43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'generatedfile',
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('format', sa.String(length=8), nullable=False),
        sa.Column('version', sa.String(length=32), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['report.id']),
        sa.PrimaryKeyConstraint('report_id', 'format'),
    )
    op.create_index('ix_generatedfile_created_at', 'generatedfile', ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_generatedfile_created_at', table_name='generatedfile')
    op.drop_table('generatedfile')
