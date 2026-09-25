"""add user category preferences

Revision ID: b3f7a9c1d5e2
Revises: 8a4a60d04029
Create Date: 2026-09-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f7a9c1d5e2'
down_revision: Union[str, Sequence[str], None] = '8a4a60d04029'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'user_category_preferences',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('category_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.uuid']),
        sa.ForeignKeyConstraint(['user_id'], ['users.uuid']),
        sa.PrimaryKeyConstraint('user_id', 'category_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user_category_preferences')
