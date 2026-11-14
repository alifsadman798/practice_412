"""0003 remove reports alerts warnings

Revision ID: 0003_cleanup
Revises: 0002_add_fare
Create Date: 2026-11-09 17:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003_cleanup"
down_revision: Union[str, None] = "0002_add_fare"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop tables
    op.execute("DROP TABLE IF EXISTS travel_alerts CASCADE")
    op.execute("DROP TABLE IF EXISTS report_reviews CASCADE")
    op.execute("DROP TABLE IF EXISTS transport_reports CASCADE")
    op.execute("DROP TABLE IF EXISTS user_warnings CASCADE")

    # 2. Drop obsolete columns from retained tables
    conn = op.get_bind()
    insp = sa.inspect(conn)

    user_cols = [c["name"] for c in insp.get_columns("users")]
    if "is_reporting_restricted" in user_cols:
        op.drop_column("users", "is_reporting_restricted")

    notif_cols = [c["name"] for c in insp.get_columns("notifications")]
    if "report_id" in notif_cols:
        op.drop_column("notifications", "report_id")

    # 3. Clean up audit logs associated exclusively with removed modules
    op.execute("""
        DELETE FROM audit_logs 
        WHERE target_type IN ('TransportReport', 'ReportReview', 'TravelAlert')
           OR action IN ('REVIEW_REPORT', 'PUBLISH_TRAVEL_ALERT', 'CREATE_TRAVEL_ALERT', 'UPDATE_TRAVEL_ALERT', 'DELETE_TRAVEL_ALERT', 'WARN_USER', 'LIFT_USER_RESTRICTION')
    """)


def downgrade() -> None:
    pass
