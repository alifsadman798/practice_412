from datetime import datetime, time, timedelta


def time_to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def minutes_to_time(minutes: int) -> time:
    minutes = minutes % (24 * 60)
    return time(minutes // 60, minutes % 60)


def calculate_duration_minutes(
    dept: time, arr: time, day_offset: int = 0
) -> int:
    dept_m = time_to_minutes(dept)
    arr_m = time_to_minutes(arr) + day_offset * 24 * 60
    if arr_m < dept_m:
        arr_m += 24 * 60
    return arr_m - dept_m


def combine_next_departure(
    base_date: datetime, dept: time, requested: datetime
) -> tuple[datetime, int]:
    departure_dt = datetime.combine(base_date.date(), dept)
    if departure_dt < requested:
        departure_dt += timedelta(days=1)
    waiting_minutes = int((departure_dt - requested).total_seconds() // 60)
    return departure_dt, max(0, waiting_minutes)
