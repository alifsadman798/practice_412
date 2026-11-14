"""0001 initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-30 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "districts",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )
    op.create_table(
        "routing_config",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "district_edges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("from_district", sa.String(length=120), nullable=False),
        sa.Column("to_district", sa.String(length=120), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.CheckConstraint("distance_km > 0", name="ck_district_distance_positive"),
        sa.CheckConstraint("from_district < to_district", name="ck_district_edge_order"),
        sa.ForeignKeyConstraint(["from_district"], ["districts.name"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_district"], ["districts.name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_district", "to_district", name="uq_district_edge"),
    )
    op.create_table(
        "locations",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("district_name", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["district_name"], ["districts.name"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("name"),
    )
    op.create_table(
        "train_services",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("train_no", sa.String(length=32), nullable=False),
        sa.Column("train_name", sa.String(length=160), nullable=False),
        sa.Column("from_district", sa.String(length=120), nullable=False),
        sa.Column("to_district", sa.String(length=120), nullable=False),
        sa.Column("off_day", sa.String(length=20), nullable=False),
        sa.Column("departure", sa.Time(), nullable=False),
        sa.Column("arrival", sa.Time(), nullable=False),
        sa.Column("day_offset", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["from_district"], ["districts.name"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_district"], ["districts.name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("train_no", name="uq_train_number"),
        sa.UniqueConstraint("train_no", "from_district", name="uq_train_direction"),
    )
    op.create_index("ix_train_no", "train_services", ["train_no"], unique=False)
    op.create_table(
        "bus_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("route_id", sa.String(length=40), nullable=False),
        sa.Column("from_district", sa.String(length=120), nullable=False),
        sa.Column("to_district", sa.String(length=120), nullable=False),
        sa.Column("transport_name", sa.String(length=160), nullable=False),
        sa.Column("departure", sa.Time(), nullable=False),
        sa.Column("arrival", sa.Time(), nullable=False),
        sa.Column("fare", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["from_district"], ["districts.name"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_district"], ["districts.name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "route_id",
            "from_district",
            "to_district",
            "transport_name",
            "departure",
            "arrival",
            name="uq_bus_schedule",
        ),
    )
    op.create_index(
        "ix_bus_lookup",
        "bus_schedules",
        ["from_district", "to_district", "departure"],
        unique=False,
    )
    op.create_table(
        "local_edges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("from_location", sa.String(length=160), nullable=False),
        sa.Column("to_location", sa.String(length=160), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("parent_district", sa.String(length=120), nullable=False),
        sa.CheckConstraint("distance_km > 0", name="ck_local_distance_positive"),
        sa.ForeignKeyConstraint(["from_location"], ["locations.name"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_district"], ["districts.name"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_location"], ["locations.name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_location", "to_location", name="uq_local_edge"),
    )
    op.create_table(
        "train_stops",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("train_no", sa.String(length=32), nullable=False),
        sa.Column("train_name", sa.String(length=160), nullable=False),
        sa.Column("stop_order", sa.Integer(), nullable=False),
        sa.Column("station", sa.String(length=160), nullable=False),
        sa.Column("district_name", sa.String(length=120), nullable=False),
        sa.Column("arrival", sa.Time(), nullable=True),
        sa.Column("departure", sa.Time(), nullable=True),
        sa.Column("day_offset", sa.Integer(), nullable=False),
        sa.Column("cumulative_km", sa.Float(), nullable=False),
        sa.CheckConstraint("stop_order > 0", name="ck_train_stop_order_positive"),
        sa.ForeignKeyConstraint(["district_name"], ["districts.name"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["train_no"], ["train_services.train_no"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("train_no", "stop_order", name="uq_train_stop_order"),
    )
    op.create_index(
        "ix_train_stop_station",
        "train_stops",
        ["district_name", "train_no"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_train_stop_station", table_name="train_stops")
    op.drop_table("train_stops")
    op.drop_table("local_edges")
    op.drop_index("ix_bus_lookup", table_name="bus_schedules")
    op.drop_table("bus_schedules")
    op.drop_index("ix_train_no", table_name="train_services")
    op.drop_table("train_services")
    op.drop_table("locations")
    op.drop_table("district_edges")
    op.drop_table("routing_config")
    op.drop_table("districts")
