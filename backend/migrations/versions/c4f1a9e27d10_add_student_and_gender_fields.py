"""add student name and teacher/student gender to report

Revision ID: c4f1a9e27d10
Revises: 6c2dc1d4307d
Create Date: 2026-11-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c4f1a9e27d10'
down_revision: Union[str, Sequence[str], None] = '6c2dc1d4307d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default fills existing rows; the defaults keep old reports' title page
    # as it was ("Виконав" / "Прийняла")
    op.add_column('report', sa.Column('teacher_gender', sqlmodel.sql.sqltypes.AutoString(length=1),
                                      nullable=False, server_default='f'))
    op.add_column('report', sa.Column('student_name', sqlmodel.sql.sqltypes.AutoString(),
                                      nullable=False, server_default=''))
    op.add_column('report', sa.Column('student_gender', sqlmodel.sql.sqltypes.AutoString(length=1),
                                      nullable=False, server_default='m'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('report', 'student_gender')
    op.drop_column('report', 'student_name')
    op.drop_column('report', 'teacher_gender')
