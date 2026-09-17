"""Regular (non-championship) Ironman races -- 2025/2026, used only by the aggregate
age-group analysis (analytics.py), not registered as individually-selectable races in
races.py. Raw JSON lives in data/raw/ironman_regular/<race_id>.json (same IMStats format
as the championship races; see parsers/ironman/common.py for the fetch/format notes).
"""
import json

from sportsplits.config import RAW_DIR
from sportsplits.parsers.ironman.common import records_to_df
from sportsplits.parsers.ironman.regular_races_manifest import FULL_RACES, HALF_RACES

_REGULAR_RAW_DIR = RAW_DIR / "ironman_regular"


def load_regular_races(races: list) -> list:
    """races: list of (race_id, name, year) tuples. Returns [(display_name, df), ...]."""
    result = []
    for race_id, name, year in races:
        records = json.loads((_REGULAR_RAW_DIR / f"{race_id}.json").read_text(encoding="utf-8"))
        result.append((f"{name} {year}", records_to_df(records)))
    return result
