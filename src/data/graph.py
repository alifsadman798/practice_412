import heapq
import math
from collections import defaultdict

from src.database.models import DistrictEdge


def shortest_path(
    edges: list[DistrictEdge], origin: str, destination: str
) -> tuple[list[str], float] | None:
    if origin == destination:
        return [origin], 0.0
    # Canonical ordering to guarantee reverse-route consistency (Section 7.3)
    reverse = origin.casefold() > destination.casefold()
    start, end = (destination, origin) if reverse else (origin, destination)
    graph: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for edge in edges:
        graph[edge.from_district].append((edge.to_district, edge.distance_km))
        graph[edge.to_district].append((edge.from_district, edge.distance_km))
    for neighbors in graph.values():
        neighbors.sort(key=lambda item: (item[0].casefold(), item[1]))

    queue: list[tuple[float, tuple[str, ...], str]] = [(0.0, (start,), start)]
    best: dict[str, tuple[float, tuple[str, ...]]] = {start: (0.0, (start,))}
    while queue:
        distance, path, node = heapq.heappop(queue)
        if best.get(node) != (distance, path):
            continue
        if node == end:
            result = list(path)
            if reverse:
                result.reverse()
            return result, distance
        for neighbor, weight in graph.get(node, []):
            next_distance = distance + weight
            next_path = path + (neighbor,)
            current = best.get(neighbor)
            if current is None or (
                math.isclose(next_distance, current[0], abs_tol=1e-9)
                and tuple(part.casefold() for part in next_path)
                < tuple(part.casefold() for part in current[1])
            ) or next_distance < current[0] - 1e-9:
                best[neighbor] = (next_distance, next_path)
                heapq.heappush(queue, (next_distance, next_path, neighbor))
    return None
