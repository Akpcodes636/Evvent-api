"""add host user role

Revision ID: 636481a882f8
Revises: c4d8e2f6a1b3
Create Date: 2026-09-29 14:45:32.033645

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "636481a882f8"
down_revision: Union[str, Sequence[str], None] = "c4d8e2f6a1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add host to the user_role_enum PostgreSQL enum."""
    op.execute(
        "ALTER TYPE user_role_enum ADD VALUE IF NOT EXISTS 'host'"
    )


def downgrade() -> None:
    """PostgreSQL does not support removing an enum value directly."""
    pass