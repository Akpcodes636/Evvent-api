"""replace event images with cloudinary image url

Revision ID: 3a3e3a6ce74c
Revises: e2f4a8b1c6d9
Create Date: 2026-10-07 09:24:58.413015

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3a3e3a6ce74c"
down_revision: Union[str, Sequence[str], None] = "e2f4a8b1c6d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Remove the old event image system.
    op.drop_index(
        op.f("ix_event_images_event_id"),
        table_name="event_images",
    )
    op.drop_index(
        op.f("ix_event_images_uuid"),
        table_name="event_images",
    )
    op.drop_table("event_images")

    # Add the single Cloudinary image URL.
    op.add_column(
        "events",
        sa.Column(
            "image_url",
            sa.String(length=500),
            nullable=True,
        ),
    )

    # Remove the old video URL.
    op.drop_column("events", "video_url")


def downgrade() -> None:
    """Downgrade schema."""

    # Restore the old video URL.
    op.add_column(
        "events",
        sa.Column(
            "video_url",
            sa.VARCHAR(length=500),
            autoincrement=False,
            nullable=True,
        ),
    )

    # Remove Cloudinary image URL.
    op.drop_column("events", "image_url")

    # Restore the old event_images table.
    op.create_table(
        "event_images",
        sa.Column(
            "uuid",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "event_id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "url",
            sa.VARCHAR(length=500),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "is_primary",
            sa.BOOLEAN(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.uuid"],
            name=op.f("event_images_event_id_fkey"),
        ),
        sa.PrimaryKeyConstraint(
            "uuid",
            name=op.f("event_images_pkey"),
        ),
    )

    op.create_index(
        op.f("ix_event_images_uuid"),
        "event_images",
        ["uuid"],
        unique=False,
    )

    op.create_index(
        op.f("ix_event_images_event_id"),
        "event_images",
        ["event_id"],
        unique=False,
    )
