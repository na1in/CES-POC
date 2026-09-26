"""Add policy_attached to audit_action_type

The attach-policy endpoint (analyst manually attaches a policy to an unmatched payment) writes a 'policy_attached'
audit entry. db/schema.sql and proto/audit.proto already had the value, but the initial migration did not, so any
database built with `alembic upgrade head` made that endpoint fail with
"invalid input value for enum audit_action_type". IF NOT EXISTS makes this a no-op on databases that were patched by hand.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-26

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE audit_action_type ADD VALUE IF NOT EXISTS 'policy_attached'")


def downgrade() -> None:
    # PostgreSQL cannot drop a single value from an enum type; the value is harmless if left in place.
    pass
