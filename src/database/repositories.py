from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import (
    BusSchedule,
    District,
    DistrictEdge,
    LocalEdge,
    TrainService,
    TrainStop,
)


class DataStore:
    def __init__(self, session: Session):
        self.session = session

    def get_districts(self) -> list[str]:
        return list(self.session.scalars(select(District.name).order_by(District.name)))

    def get_district_graph(self) -> list[DistrictEdge]:
        return list(self.session.scalars(select(DistrictEdge)))

    def get_local_graph(self) -> list[LocalEdge]:
        return self.get_local_edges()

    def get_parent_of(self, upazila_name: str) -> str | None:
        edge = self.session.scalar(
            select(LocalEdge)
            .where(LocalEdge.from_location.ilike(upazila_name.strip()))
            .limit(1)
        )
        return edge.parent_district if edge else None

    def get_bus_schedules(self, from_d: str, to_d: str) -> list[BusSchedule]:
        return list(
            self.session.scalars(
                select(BusSchedule).where(
                    BusSchedule.from_district == from_d,
                    BusSchedule.to_district == to_d,
                )
            )
        )

    def get_train_routes(self) -> list[TrainService]:
        return list(self.session.scalars(select(TrainService)))

    def get_train_stops(self, train_no: str) -> list[TrainStop]:
        return list(
            self.session.scalars(
                select(TrainStop)
                .where(TrainStop.train_no == train_no)
                .order_by(TrainStop.stop_order)
            )
        )

    def get_local_edges(self) -> list[LocalEdge]:
        return list(self.session.scalars(select(LocalEdge)))
