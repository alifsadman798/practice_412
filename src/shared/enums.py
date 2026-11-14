from enum import StrEnum


class Mode(StrEnum):
    BUS = "bus"
    TRAIN = "train"
    LOCAL = "local"


class RouteKind(StrEnum):
    BUS = "bus"
    TRAIN = "train"
    MULTIMODAL = "multimodal"


class Preference(StrEnum):
    FASTEST = "fastest"
    CHEAPEST = "cheapest"
    SHORTEST = "shortest"
    BALANCED = "balanced"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
