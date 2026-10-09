"""stage 6: receipt image fingerprint (perceptual hash) for duplicate detection

NULL for receipts uploaded before this revision (they are still compared by exact file hash
and by store/paid_at/total).

Revision ID: 8cbe05831b00
Revises: f88f6dc64030
Create Date: 2026-10-10 01:34:34.350948

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8cbe05831b00'
down_revision: Union[str, Sequence[str], None] = 'f88f6dc64030'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('receipts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_phash', sa.String(length=64), nullable=True))



def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('receipts', schema=None) as batch_op:
        batch_op.drop_column('image_phash')

