from src.shared.constants import (
    BUS_TRANSFER_BUFFER_MINUTES,
    LOCAL_TRANSFER_BUFFER_MINUTES,
    TRAIN_TRANSFER_BUFFER_MINUTES,
)


def get_transfer_buffer_minutes(from_mode: str, to_mode: str) -> int:
    if "local" in (from_mode, to_mode):
        return LOCAL_TRANSFER_BUFFER_MINUTES
    return max(BUS_TRANSFER_BUFFER_MINUTES, TRAIN_TRANSFER_BUFFER_MINUTES)
