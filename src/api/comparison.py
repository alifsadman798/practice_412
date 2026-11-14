from src.shared.models import Comparison, RouteOption


def build_comparison(routes: list[RouteOption]) -> Comparison:
    if not routes:
        return Comparison(note="No scheduled route is available for this journey.")
    cheapest = min(routes, key=lambda route: (route.fare_bdt, route.distance_km))
    fastest = min(
        routes,
        key=lambda route: (
            route.travel_time.expected_minutes + route.waiting_minutes,
            route.fare_bdt,
        ),
    )
    shortest = min(routes, key=lambda route: (route.distance_km, route.fare_bdt))
    labels = []
    if cheapest:
        labels.append(f"{cheapest.kind.value} is cheapest")
    if fastest:
        labels.append(f"{fastest.kind.value} is fastest")
    if shortest:
        labels.append(f"{shortest.kind.value} is shortest")
    return Comparison(
        cheapest=cheapest,
        fastest=fastest,
        shortest=shortest,
        note=", ".join(labels) + ".",
    )
