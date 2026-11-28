"""report kind (lab / essay), essay title page fields, introduction, bibliography, LaTeX mode

Revision ID: e1b9f04c6a27
Revises: d7a2c5e81b34
Create Date: 2026-11-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'e1b9f04c6a27'
down_revision: Union[str, Sequence[str], None] = 'd7a2c5e81b34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('report', sa.Column('kind', _STR(length=8), nullable=False, server_default='lab'))
    for name in ('faculty', 'department', 'teacher_position', 'work_date'):
        op.add_column('report', sa.Column(name, _STR(), nullable=False, server_default=''))
    op.add_column('report', sa.Column('introduction', sa.Text(), nullable=True))
    op.add_column('report', sa.Column('bibliography', sa.JSON(), nullable=True))
    op.add_column('report', sa.Column('editor_mode', _STR(length=8), nullable=False, server_default='form'))
    op.add_column('report', sa.Column('latex_source', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    for name in ('latex_source', 'editor_mode', 'bibliography', 'introduction',
                 'work_date', 'teacher_position', 'department', 'faculty', 'kind'):
        op.drop_column('report', name)
