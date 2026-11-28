"""any institution: level (university / school), ministry, institution, city; user profile

Revision ID: f3c8a1d5e902
Revises: e1b9f04c6a27
Create Date: 2026-11-28 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'f3c8a1d5e902'
down_revision: Union[str, Sequence[str], None] = 'e1b9f04c6a27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('report', sa.Column('level', _STR(length=16), nullable=False, server_default='university'))
    op.add_column('report', sa.Column('ministry', _STR(), nullable=False,
                                      server_default='Міністерство освіти і науки України'))
    # Reports made before templates were ХНУРЕ ones: keep their title page as it was
    op.add_column('report', sa.Column('institution', _STR(), nullable=False,
                                      server_default='Харківський національний університет радіоелектроніки'))
    op.add_column('report', sa.Column('city', _STR(), nullable=False, server_default='Харків'))
    op.execute("UPDATE report SET department = 'штучного інтелекту' WHERE kind = 'lab' AND department = ''")
    # New reports get their values from the form / user profile, not from these defaults
    op.alter_column('report', 'institution', server_default='')
    op.alter_column('report', 'city', server_default='')
    op.add_column('user', sa.Column('profile', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user', 'profile')
    for name in ('city', 'institution', 'ministry', 'level'):
        op.drop_column('report', name)
