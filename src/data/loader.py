import csv
from datetime import datetime, time
from pathlib import Path


def resolve_dataset_path(data_dir: Path, primary_name: str, alternatives: tuple[str, ...] = ()) -> Path:
    candidates = (primary_name,) + alternatives
    for name in candidates:
        candidate = data_dir / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Required dataset is missing in {data_dir}. Looked for: {', '.join(candidates)}"
    )


def read_csv(data_dir: Path, primary_name: str, alternatives: tuple[str, ...] = ()) -> list[dict[str, str]]:
    path = resolve_dataset_path(data_dir, primary_name, alternatives)
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"Dataset has no header: {path}")
        return [
            {
                (key.strip() if key else ""): (value.strip() if value else "")
                for key, value in row.items()
                if key
            }
            for row in reader
        ]


def required_text(row: dict[str, str], key: str, filename: str) -> str:
    value = row.get(key, "").strip()
    if not value:
        raise ValueError(f"{filename}: required value '{key}' is blank")
    return value


def positive_distance(row: dict[str, str], filename: str) -> float:
    value = float(required_text(row, "Distance_km", filename))
    if value <= 0:
        raise ValueError(f"{filename}: Distance_km must be positive")
    return value


def parse_time(value: str, filename: str, *, optional: bool = False) -> time | None:
    value = (value or "").strip()
    if not value and optional:
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise ValueError(f"{filename}: invalid 24-hour time '{value}'") from exc


def parse_day_offset(value: str | None) -> int:
    if not value:
        return 0
    try:
        return int(float(value.strip()))
    except (ValueError, TypeError):
        return 0


def parse_float_km(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return float(value.strip())
    except (ValueError, TypeError):
        return 0.0
