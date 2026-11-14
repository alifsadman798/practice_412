"""0004 remove notifications

Revision ID: 0004_remove_notifications
Revises: 0003_cleanup
Create Date: 2026-11-09 17:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004_remove_notifications"
down_revision: Union[str, None] = "0003_cleanup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop notifications table and any associated indexes/foreign keys
    op.execute("DROP TABLE IF EXISTS notifications CASCADE")


def downgrade() -> None:
    pass
