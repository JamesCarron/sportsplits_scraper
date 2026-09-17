"""Parser for Ironman World Championship results, sourced from CoachCox's IMStats
(coachcox.co.uk) public JSON API.

The raw files under ``data/raw/ironman/<race_id>.json`` are verbatim dumps of
``https://www.coachcox.co.uk/wp-json/imstats/v1.92/race/results/<race_id>`` -- one
record per athlete, fetched by hand through a browser (not an automated scraper;
both ironman.com and coachcox.co.uk disallow AI crawlers in robots.txt). This
module only maps that JSON to the standard 13-column format described in
docs/DATA_FORMAT.md; it does no fetching.

Field mapping notes:
- Splits (``st``/``t1t``/``bt``/``t2t``/``rt``/``ot``) are plain integer seconds,
  unlike RaceResult's "H:MM:SS" strings.
- ``g`` (Male/Female) maps to Class the same way RaceResult's class_map does
  ("Open"/"Female"), so the app's existing Class-based views work unchanged.
- There is no club field in this source; Club holds the athlete's country instead.
- ``or``/``odr`` (overall/division rank) are ``0`` (not absent) for non-finishers --
  treated as "no rank", not an actual placement.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from sportsplits.config import RAW_DIR, PROCESSED_DIR
from sportsplits.parsers.raceresult.common import STANDARD_COLS, save_processed

_CLASS_MAP = {"Male": "Open", "Female": "Female"}

_IRONMAN_RAW_DIR = RAW_DIR / "ironman"


@dataclass
class IronmanEventSpec:
    """Everything needed to identify and register one Ironman World Championship race."""
    race_id: str
    name: str                # registry / display name
    distance: str             # "full" | "70.3"
    processed_filename: str

    @property
    def raw_path(self) -> Path:
        return _IRONMAN_RAW_DIR / f"{self.race_id}.json"

    @property
    def processed_path(self) -> Path:
        return PROCESSED_DIR / self.processed_filename


def slugify(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or "race"


def _seconds_to_timedelta(v) -> pd.Timedelta:
    """Convert a plain-integer seconds value (int or numeric string) to a Timedelta."""
    if v in (None, ""):
        return pd.NaT
    try:
        return pd.Timedelta(seconds=int(v))
    except (TypeError, ValueError):
        return pd.NaT


def _to_int(v):
    if v in (None, ""):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _to_rank(v):
    """Like _to_int, but 0 means "no rank" (IMStats' sentinel for non-finishers)."""
    n = _to_int(v)
    return n if n else None


def records_to_df(records: list) -> pd.DataFrame:
    """Map raw IMStats athlete records (parsed JSON) to the standard 13-column format."""
    rows = []
    for r in records:
        rows.append({
            "Place":      _to_rank(r.get("or")),
            "Bib":        _to_int(r.get("bi")),
            "Name":       r.get("n") or "",
            "Age_Group":  r.get("di") or "",
            "Group_Rank": _to_rank(r.get("odr")),
            "Class":      _CLASS_MAP.get(r.get("g"), r.get("g") or ""),
            "Club":       r.get("c") or "",
            "Swim":       _seconds_to_timedelta(r.get("st")),
            "T1":         _seconds_to_timedelta(r.get("t1t")),
            "Bike":       _seconds_to_timedelta(r.get("bt")),
            "T2":         _seconds_to_timedelta(r.get("t2t")),
            "Run":        _seconds_to_timedelta(r.get("rt")),
            "Finish":     _seconds_to_timedelta(r.get("ot")),
        })

    df = pd.DataFrame(rows, columns=STANDARD_COLS)
    if not df.empty:
        df = df.sort_values("Place", na_position="last").reset_index(drop=True)
        df["Place"] = df["Place"].astype("Int64")
        df["Group_Rank"] = df["Group_Rank"].astype("Int64")
    return df


def parse_event(spec: IronmanEventSpec) -> pd.DataFrame:
    """Build the standard 13-column DataFrame from this race's raw IMStats JSON."""
    records = json.loads(spec.raw_path.read_text(encoding="utf-8"))
    return records_to_df(records)


def process_event(spec: IronmanEventSpec) -> Path:
    """Read this race's raw JSON and (re)write its processed CSV. Idempotent."""
    df = parse_event(spec)
    return save_processed(df, spec.processed_path)


def process_all(specs: list) -> dict:
    """Process every given event. Returns {name: processed_csv_path}."""
    return {spec.name: process_event(spec) for spec in specs}
