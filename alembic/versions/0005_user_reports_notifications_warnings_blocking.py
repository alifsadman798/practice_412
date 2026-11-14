"""0005 user reports notifications warnings blocking

Revision ID: 0005_reports_and_moderation
Revises: 0004_remove_notifications
Create Date: 2026-11-13 15:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005_reports_and_moderation"
down_revision: Union[str, None] = "0004_remove_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # 1. Add moderation columns to users if not present
    user_cols = [c["name"] for c in insp.get_columns("users")]
    if "is_blocked" not in user_cols:
        op.add_column("users", sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    if "blocked_reason" not in user_cols:
        op.add_column("users", sa.Column("blocked_reason", sa.Text(), nullable=True))
    if "blocked_at" not in user_cols:
        op.add_column("users", sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True))
    if "blocked_by" not in user_cols:
        op.add_column("users", sa.Column("blocked_by", sa.String(length=80), nullable=True))

    # 2. Create user_reports table if not present
    tables = insp.get_table_names()
    if "user_reports" not in tables:
        op.create_table(
            "user_reports",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("report_id", sa.String(length=32), nullable=False),
            sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("category", sa.String(length=80), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("transport_mode", sa.String(length=40), server_default="General", nullable=True),
            sa.Column("related_route_info", sa.String(length=255), nullable=True),
            sa.Column("evidence_path", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
            sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("reviewed_by", sa.String(length=80), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("admin_response", sa.Text(), nullable=True),
            sa.Column("user_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("admin_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        )
        op.create_index("ix_reports_report_id", "user_reports", ["report_id"], unique=True)
        op.create_index("ix_reports_user", "user_reports", ["user_id"])
        op.create_index("ix_reports_status", "user_reports", ["status"])
        op.create_index("ix_reports_submitted", "user_reports", ["submitted_at"])

    # 3. Create notifications table if not present
    if "notifications" not in tables:
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("report_id", sa.String(length=32), nullable=True),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("notification_type", sa.String(length=40), server_default="general", nullable=False),
            sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_notif_user_read", "notifications", ["user_id", "is_read"])
        op.create_index("ix_notif_created", "notifications", ["created_at"])

    # 4. Create user_warnings table if not present
    if "user_warnings" not in tables:
        op.create_table(
            "user_warnings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("admin_id", sa.String(length=80), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_warnings_user", "user_warnings", ["user_id"])
        op.create_index("ix_warnings_created", "user_warnings", ["created_at"])

    # 5. Create user_block_history table if not present
    if "user_block_history" not in tables:
        op.create_table(
            "user_block_history",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("admin_id", sa.String(length=80), nullable=False),
            sa.Column("action", sa.String(length=20), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_block_history_user", "user_block_history", ["user_id"])
        op.create_index("ix_block_history_created", "user_block_history", ["created_at"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_block_history CASCADE")
    op.execute("DROP TABLE IF EXISTS user_warnings CASCADE")
    op.execute("DROP TABLE IF EXISTS notifications CASCADE")
    op.execute("DROP TABLE IF EXISTS user_reports CASCADE")
