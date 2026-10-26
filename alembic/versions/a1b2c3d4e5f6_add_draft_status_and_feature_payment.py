"""add draft status and feature payment reference

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-10-26 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'draft' value to the existing event_status_enum type.
    # IF NOT EXISTS is available from PostgreSQL 9.3+.
    op.execute("ALTER TYPE event_status_enum ADD VALUE IF NOT EXISTS 'draft'")

    # Add the column that stores a Paystack reference for feature fee payments.
    op.add_column(
        "events",
        sa.Column(
            "feature_paystack_reference",
            sa.String(length=200),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values once added, so we can
    # only undo the column addition here.
    op.drop_column("events", "feature_paystack_reference")
