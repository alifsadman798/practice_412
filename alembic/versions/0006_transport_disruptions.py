"""0006 transport disruptions and route alerts

Revision ID: 0006_transport_disruptions
Revises: 0005_reports_and_moderation
Create Date: 2026-11-13 16:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006_transport_disruptions"
down_revision: Union[str, None] = "0005_reports_and_moderation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()

    # 1. transport_disruptions table
    if "transport_disruptions" not in tables:
        op.create_table(
            "transport_disruptions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("disruption_id", sa.String(length=32), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("location_name", sa.String(length=120), nullable=False),
            sa.Column("transport_mode", sa.String(length=20), nullable=False),
            sa.Column("cause", sa.String(length=60), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False, server_default="MODERATE"),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("alert_message", sa.Text(), nullable=False),
            sa.Column("source_name", sa.String(length=160), nullable=True),
            sa.Column("source_url", sa.String(length=500), nullable=True),
            sa.Column("source_published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("admin_notes", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
            sa.Column("estimated_end_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by_admin_id", sa.String(length=80), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_disruptions_disruption_id", "transport_disruptions", ["disruption_id"], unique=True)
        op.create_index("ix_disruptions_status", "transport_disruptions", ["status"])
        op.create_index("ix_disruptions_location", "transport_disruptions", ["location_name"])
        op.create_index("ix_disruptions_mode", "transport_disruptions", ["transport_mode"])
        op.create_index("ix_disruptions_created", "transport_disruptions", ["created_at"])

    # 2. disruption_affected_segments table
    if "disruption_affected_segments" not in tables:
        op.create_table(
            "disruption_affected_segments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("disruption_id", sa.Integer(), sa.ForeignKey("transport_disruptions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("transport_mode", sa.String(length=20), nullable=False),
            sa.Column("affected_segment_id", sa.String(length=120), nullable=False),
            sa.Column("segment_description", sa.String(length=255), nullable=False),
            sa.Column("from_point", sa.String(length=120), nullable=True),
            sa.Column("to_point", sa.String(length=120), nullable=True),
        )
        op.create_index("ix_affected_disruption", "disruption_affected_segments", ["disruption_id"])
        op.create_index("ix_affected_mode_seg", "disruption_affected_segments", ["transport_mode", "affected_segment_id"])

    # 3. disruption_audit_logs table
    if "disruption_audit_logs" not in tables:
        op.create_table(
            "disruption_audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("disruption_id", sa.Integer(), nullable=False),
            sa.Column("admin_id", sa.String(length=80), nullable=False),
            sa.Column("action", sa.String(length=40), nullable=False),
            sa.Column("previous_status", sa.String(length=20), nullable=True),
            sa.Column("new_status", sa.String(length=20), nullable=False),
            sa.Column("change_description", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_disruption_audit_disruption", "disruption_audit_logs", ["disruption_id"])
        op.create_index("ix_disruption_audit_created", "disruption_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("disruption_audit_logs")
    op.drop_table("disruption_affected_segments")
    op.drop_table("transport_disruptions")
