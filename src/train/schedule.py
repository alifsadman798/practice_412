from datetime import date


def is_off_day(off_day: str, travel_date: date) -> bool:
    return off_day.strip().casefold() == travel_date.strftime("%A").casefold()
