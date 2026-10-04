"""Reword threshold descriptions: nothing auto-applies in PayWise

Every payment lands HELD for an analyst, so "auto-apply" / "auto-approve" in the threshold descriptions was wrong.
Only the description text changes; parameter values and history are untouched.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-03

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW = {
    "name_match_auto_apply": "Min name similarity % for an Apply recommendation (Scenario 1)",
    "amount_tolerance_auto": "Max variance % for an Apply recommendation (Scenario 1)",
}
_OLD = {
    "name_match_auto_apply": "Min name similarity % for Scenario 1 auto-apply",
    "amount_tolerance_auto": "Max variance % for auto-approve (Scenario 1)",
}


def _set(descriptions: dict) -> None:
    for name, text in descriptions.items():
        op.execute(
            "UPDATE configuration_thresholds SET description = '%s' WHERE parameter_name = '%s'" % (text.replace("'", "''"), name)
        )


def upgrade() -> None:
    _set(_NEW)


def downgrade() -> None:
    _set(_OLD)
