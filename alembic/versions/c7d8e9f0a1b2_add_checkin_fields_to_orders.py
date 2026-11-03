"""add checkin fields to orders

Revision ID: c7d8e9f0a1b2
Revises: b5c6d7e8f9a0
Create Date: 2026-11-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, None] = "b5c6d7e8f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("checked_in", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "orders",
        sa.Column("checked_in_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "checked_in_at")
    op.drop_column("orders", "checked_in")
