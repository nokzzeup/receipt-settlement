"""stage 5: budget period on organizations + more approval actions

- organizations.budget_period_start / budget_period_end (DATE, both NULL = no period)
- approval_logs.action: add WITHDRAW, UNAPPROVE, UNREIMBURSE
  (non-native enum = VARCHAR(20) + CHECK, so the CHECK constraint is replaced)

Hand-written: autogenerate does not detect CHECK constraint or enum value changes.

Revision ID: f88f6dc64030
Revises: 928bd1830b7f
Create Date: 2026-10-10 01:13:24.073639

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f88f6dc64030"
down_revision: Union[str, Sequence[str], None] = "928bd1830b7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_ACTIONS = ("SUBMIT", "APPROVE", "REJECT", "REIMBURSE")
NEW_ACTIONS = ("SUBMIT", "WITHDRAW", "APPROVE", "UNAPPROVE", "REJECT", "REIMBURSE", "UNREIMBURSE")


def _action_enum(values: Sequence[str]) -> sa.Enum:
    return sa.Enum(*values, name="approval_action", native_enum=False, create_constraint=True, length=20)


def upgrade() -> None:
    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("budget_period_start", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("budget_period_end", sa.Date(), nullable=True))
        batch_op.create_check_constraint(
            "budget_period_together", "(budget_period_start IS NULL) = (budget_period_end IS NULL)"
        )
        batch_op.create_check_constraint(
            "budget_period_order", "budget_period_start IS NULL OR budget_period_start <= budget_period_end"
        )

    with op.batch_alter_table("approval_logs", schema=None) as batch_op:
        batch_op.alter_column(
            "action",
            existing_type=_action_enum(OLD_ACTIONS),
            type_=_action_enum(NEW_ACTIONS),
            existing_nullable=False,
        )


def downgrade() -> None:
    # rows using the new actions cannot be represented in the old CHECK constraint
    op.execute("DELETE FROM approval_logs WHERE action IN ('WITHDRAW', 'UNAPPROVE', 'UNREIMBURSE')")
    with op.batch_alter_table("approval_logs", schema=None) as batch_op:
        batch_op.alter_column(
            "action",
            existing_type=_action_enum(NEW_ACTIONS),
            type_=_action_enum(OLD_ACTIONS),
            existing_nullable=False,
        )

    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.drop_constraint("budget_period_order", type_="check")
        batch_op.drop_constraint("budget_period_together", type_="check")
        batch_op.drop_column("budget_period_end")
        batch_op.drop_column("budget_period_start")
