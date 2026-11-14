from src.database.models import DistrictEdge
from src.data.graph import shortest_path


def get_shortest_bus_path(
    edges: list[DistrictEdge], origin: str, destination: str
) -> tuple[list[str], float] | None:
    return shortest_path(edges, origin, destination)
