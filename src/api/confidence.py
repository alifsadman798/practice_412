from src.shared.models import Confidence, RouteKind


def calculate_confidence(kind: RouteKind, has_local_leg: bool = False) -> Confidence:
    if has_local_leg:
        return Confidence.LOW
    if kind == RouteKind.TRAIN:
        return Confidence.HIGH
    return Confidence.MEDIUM
