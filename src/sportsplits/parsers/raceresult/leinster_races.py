"""Leinster/East-region Irish races found via the full Triathlon Ireland calendar
sweep (2024-2026), reachable through my.raceresult.com but on RaceResult accounts
that don't carry a separate gender/class column -- gender lives only as an "M"/"F"
prefix on the age-group text, and that text uses spaced dashes ("M35 - 39") rather
than the app's standard "M35-39"/"25-29" band format.

Common.py's EventSpec/process_event() has no hook for deriving Class from another
column or reformatting Age_Group, and it's shared infrastructure used by every
other race source -- so instead of changing it, `_fixup` re-derives Class and
re-normalises Age_Group here, as a second pass over the processed CSV it wrote.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from sportsplits.parsers.raceresult.common import (
    EventSpec, build_event, load_processed_csv, save_processed,
)

_SPACED_BAND_RE = re.compile(r"^([MF])\s*(\d{1,2})\s*-\s*(\d{1,2})$")


def _fixup(path) -> None:
    """Re-derive Class from the Age_Group gender prefix and tighten 'M35 - 39' ->
    'M35-39' so analytics.py's band regex (no spaces) matches."""
    df = load_processed_csv(path)

    def fix_one(band: str):
        m = _SPACED_BAND_RE.match((band or "").strip())
        if not m:
            return band, ""
        gender, lo, hi = m.groups()
        cls = "Open" if gender == "M" else "Female"
        return f"{gender}{lo}-{hi}", cls

    fixed = df["Age_Group"].map(fix_one)
    df["Age_Group"] = fixed.map(lambda t: t[0])
    df["Class"] = fixed.map(lambda t: t[1])
    save_processed(df, path)


@dataclass
class LeinsterRace:
    event_id: str
    contest: str
    name: str
    processed_filename: str

    @property
    def processed_path(self):
        return EventSpec(
            event_id=self.event_id, name=self.name,
            processed_filename=self.processed_filename,
            main_list="", contest=self.contest,
        ).processed_path

    def to_spec(self) -> EventSpec:
        return EventSpec(
            event_id=self.event_id,
            name=self.name,
            processed_filename=self.processed_filename,
            main_list="02-Results|Triathlon Results",
            ag_list=None,
            place_idx=2, bib_idx=0, id_idx=1, name_idx=3, name_format="plain",
            class_idx=5, class_map=None,  # placeholder; _fixup() derives the real Class
            club_idx=4, agegroup_idx=5,
            split_idx=(8, 9, 10, 11, 12, 14),
            contest=self.contest,
        )


# TriLaois 2025 (Portlaoise, 2025-04-12) -- pool-based triathlon, RaceResult event
# 335336. Two individual contests published (relay contests 3/4 skipped -- no
# splits data of interest for age-group analysis).
RACES = [
    LeinsterRace("335336", "1", "TriLaois 2025 - Sprint Triathlon", "TriLaois_2025_Sprint.csv"),
    LeinsterRace("335336", "2", "TriLaois 2025 - Try-a-Tri", "TriLaois_2025_TryATri.csv"),
]


def build_all() -> dict:
    """Scrape + process every race here, fix up Class/Age_Group, return {name: df}."""
    out = {}
    for race in RACES:
        spec = race.to_spec()
        path = build_event(spec)
        _fixup(path)
        out[race.name] = load_processed_csv(path)
    return out


if __name__ == "__main__":
    results = build_all()
    for name, df in results.items():
        print(name, len(df), "rows")
