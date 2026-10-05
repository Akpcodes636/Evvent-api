"""replace role column with account_type

Revision ID: e2f4a8b1c6d9
Revises: d1e3f7a2c9b4
Create Date: 2026-10-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2f4a8b1c6d9"
down_revision: Union[str, Sequence[str], None] = "d1e3f7a2c9b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the new account_type enum with all three values
    op.execute(
        "CREATE TYPE account_type_enum AS ENUM ('individual', 'organization', 'admin')"
    )

    # 2. Add account_type column as nullable initially so we can populate it
    op.add_column(
        "users",
        sa.Column(
            "account_type",
            sa.Enum("individual", "organization", "admin", name="account_type_enum"),
            nullable=True,
        ),
    )

    # 3. Migrate data from the old role column
    op.execute("UPDATE users SET account_type = 'admin' WHERE role = 'admin'")
    op.execute("UPDATE users SET account_type = 'individual' WHERE role IN ('host', 'attendee')")

    # 4. Make account_type non-nullable now that all rows have a value
    op.alter_column("users", "account_type", nullable=False)

    # 5. Add index on account_type
    op.create_index("ix_users_account_type", "users", ["account_type"])

    # 6. Drop the old role column and its enum
    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "role")
    op.execute("DROP TYPE user_role_enum")


def downgrade() -> None:
    # Recreate the old role enum and column
    op.execute(
        "CREATE TYPE user_role_enum AS ENUM ('attendee', 'host', 'admin')"
    )
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.Enum("attendee", "host", "admin", name="user_role_enum"),
            nullable=True,
        ),
    )
    op.execute("UPDATE users SET role = 'admin' WHERE account_type = 'admin'")
    op.execute("UPDATE users SET role = 'host' WHERE account_type IN ('individual', 'organization')")
    op.alter_column("users", "role", nullable=False)
    op.create_index("ix_users_role", "users", ["role"])

    # Drop the new account_type column and enum
    op.drop_index("ix_users_account_type", table_name="users")
    op.drop_column("users", "account_type")
    op.execute("DROP TYPE account_type_enum")
