
"""add paystack reference to orders

Revision ID: 4914e248b6d7
Revises: 485d6a18c25b
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "4914e248b6d7"
down_revision: Union[str, Sequence[str], None] = "485d6a18c25b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("paystack_reference", sa.String(length=200), nullable=True),
    )
    op.create_unique_constraint(
        "uq_orders_paystack_reference",
        "orders",
        ["paystack_reference"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_orders_paystack_reference",
        "orders",
        type_="unique",
    )
    op.drop_column("orders", "paystack_reference")
