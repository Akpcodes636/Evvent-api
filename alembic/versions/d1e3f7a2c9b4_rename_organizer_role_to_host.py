"""rename organizer role to host

Revision ID: d1e3f7a2c9b4
Revises: 636481a882f8
Create Date: 2026-09-29 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d1e3f7a2c9b4"
down_revision: Union[str, Sequence[str], None] = "636481a882f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Cast the column to text first so we can use any string value
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE text USING role::text"
    )

    # 2. Migrate legacy role values to their current equivalents
    op.execute("UPDATE users SET role = 'host' WHERE role = 'organizer'")
    op.execute("UPDATE users SET role = 'attendee' WHERE role = 'user'")

    # 3. Drop the old enum (no longer bound to any column)
    op.execute("DROP TYPE user_role_enum")

    # 4. Recreate it with only the correct values
    op.execute(
        "CREATE TYPE user_role_enum AS ENUM ('attendee', 'host', 'admin')"
    )

    # 5. Restore the column to the new enum type
    op.execute(
        "ALTER TABLE users ALTER COLUMN role "
        "TYPE user_role_enum USING role::user_role_enum"
    )


def downgrade() -> None:
    # Restore 'organizer' value (data that was 'organizer' is lost — kept as 'host')
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE text USING role::text"
    )
    op.execute("DROP TYPE user_role_enum")
    op.execute(
        "CREATE TYPE user_role_enum AS ENUM ('attendee', 'organizer', 'host', 'admin')"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN role "
        "TYPE user_role_enum USING role::user_role_enum"
    )
