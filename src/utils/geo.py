def normalize_location_name(name: str) -> str:
    return name.strip().title() if name else ""
