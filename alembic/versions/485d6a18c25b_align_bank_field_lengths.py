"""align bank field lengths

Revision ID: 485d6a18c25b
Revises: 3a3e3a6ce74c
Create Date: 2026-10-07 09:48:57.482505

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "485d6a18c25b"
down_revision: Union[str, Sequence[str], None] = "3a3e3a6ce74c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "users",
        "bank_name",
        existing_type=sa.VARCHAR(length=200),
        type_=sa.String(length=100),
        existing_nullable=True,
    )

    op.alter_column(
        "users",
        "bank_account_number",
        existing_type=sa.VARCHAR(length=100),
        type_=sa.String(length=34),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "users",
        "bank_account_number",
        existing_type=sa.String(length=34),
        type_=sa.VARCHAR(length=100),
        existing_nullable=True,
    )

    op.alter_column(
        "users",
        "bank_name",
        existing_type=sa.String(length=100),
        type_=sa.VARCHAR(length=200),
        existing_nullable=True,
    )
