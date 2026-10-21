"""add carts table

Revision ID: f1a2b3c4d5e6
Revises: d497a1baf19b
Create Date: 2026-10-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "d497a1baf19b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "carts",
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("attendees", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.uuid"]),
        sa.ForeignKeyConstraint(["ticket_type_id"], ["ticket_types.uuid"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.uuid"]),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(op.f("ix_carts_uuid"), "carts", ["uuid"], unique=False)
    op.create_index(op.f("ix_carts_user_id"), "carts", ["user_id"], unique=False)
    op.create_index(op.f("ix_carts_event_id"), "carts", ["event_id"], unique=False)
    op.create_index(op.f("ix_carts_ticket_type_id"), "carts", ["ticket_type_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_carts_ticket_type_id"), table_name="carts")
    op.drop_index(op.f("ix_carts_event_id"), table_name="carts")
    op.drop_index(op.f("ix_carts_user_id"), table_name="carts")
    op.drop_index(op.f("ix_carts_uuid"), table_name="carts")
    op.drop_table("carts")
