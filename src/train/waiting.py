from datetime import datetime, timedelta
from src.database.models import TrainService
from src.train.schedule import is_off_day


def next_train_date(service: TrainService, requested: datetime) -> datetime:
    current_date = requested.date()
    # Check up to 8 days to find an operating day
    for _ in range(8):
        if not is_off_day(service.off_day, current_date):
            break
        current_date += timedelta(days=1)
    dep_time = datetime.combine(current_date, service.departure)
    while dep_time < requested:
        current_date += timedelta(days=1)
        while is_off_day(service.off_day, current_date):
            current_date += timedelta(days=1)
        dep_time = datetime.combine(current_date, service.departure)
    return dep_time
