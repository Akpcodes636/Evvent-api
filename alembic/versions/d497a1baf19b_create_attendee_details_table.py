
"""create attendee details table"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d497a1baf19b"
down_revision: Union[str, Sequence[str], None] = "4914e248b6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attendee_details",
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_index", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.uuid"]),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(
        op.f("ix_attendee_details_uuid"),
        "attendee_details",
        ["uuid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_attendee_details_order_id"),
        "attendee_details",
        ["order_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_attendee_details_order_id"),
        table_name="attendee_details",
    )
    op.drop_index(
        op.f("ix_attendee_details_uuid"),
        table_name="attendee_details",
    )
    op.drop_table("attendee_details")
