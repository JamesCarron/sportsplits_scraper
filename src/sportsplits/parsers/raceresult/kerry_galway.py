"""Kerry + Galway (+ a couple of other counties) Irish triathlon races, 2024-2026 --
found via the same "Full systematic sweep" that produced Monster Timing and
Sportsplits: these are ordinary my.raceresult.com events run by small regional
clubs/organisers (Hardman Events in South Kerry, Tri Lakes Triathlon Club and
Loughrea Triathlon Club in Galway), not affiliated with either of the two
platforms already integrated.

Two account styles were found among them (see RACES below for which is which):

* "inline" -- the per-athlete results list already carries SEX and an
  age-group band column (e.g. Ballinskelligs, Cromane, Tri Lakes). Columns are
  located by keyword match against DataFields, same approach as
  monster_timing.py, since positions vary between events.
* "agejoin" -- the results list (often named "Online|Final", a newer/simpler
  RaceResult template) has splits and a name but no sex column at all; a
  separate "Age Group ... - Win" list on the same event has FIRSTNAME/LASTNAME/
  YEAR/SEX/CLUB per participant (id-matched) but only the finish time, no
  splits. Built by joining the two on RaceResult's internal ID. Age_Group band
  is then derived from YEAR (age = race year - birth year, bucketed into the
  standard 5-year bands) since these lists don't publish a band field directly.

Skipped on purpose (found via search but not pulled):
* Hardman Killarney 2025 and Cromane Duathlon 2025 -- both are actually
  run-bike-run duathlons this edition (no swim leg), which doesn't fit the
  Swim/T1/Bike/T2/Run/Finish standard format.
* Loughrea Predator Triathlon 2025 (event 353622) -- the RaceResult account's
  published config only exposes a "Under 9's" kids category; the adult race
  results aren't published there.
* Cromane Triathlon 2026 (event 423479, 2026-09-19) -- race hadn't happened
  yet as of this sweep (2026-09-17).
* Tri Lakes Connemara Sprint Triathlon 2026 (event 372579) -- already covered
  by monster_timing_manifest.py (Monster Timing is itself RaceResult-powered
  and this event is listed under both; don't double-count it).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from sportsplits.config import RAW_DIR, PROCESSED_DIR
from sportsplits.parsers.raceresult.common import (
    RaceResultClient,
    STANDARD_COLS,
    to_timedelta,
    to_int,
    format_name,
    save_processed,
)

_RAW_DIR = RAW_DIR / "kerry_galway"

_SPLIT_KEYWORDS = [
    ("Swim", ["swim", "afterswim"]),
    ("T1", ["transition1", "t1"]),
    ("Bike", ["bike", "cycle"]),
    ("T2", ["transition2", "t2"]),
    ("Run", ["run"]),
    ("Finish", ["time", "total"]),
]

AG_BANDS = [(18, 24)] + [(s, s + 4) for s in range(25, 85, 5)]


def _band_from_age(age: int | None) -> str:
    if age is None or age < 18:
        return ""
    for lo, hi in AG_BANDS:
        if lo <= age <= hi:
            return f"{lo}-{hi}"
    return ""


def _class_from_sex(s: str) -> str:
    s = (s or "").strip().lower()
    if s.startswith("f"):
        return "Female"
    if s.startswith("m"):
        return "Open"
    return ""


def _find_field(datafields: list, keywords: list, exclude: set) -> int | None:
    low = [f.lower() for f in datafields]
    for i, f in enumerate(low):
        if i in exclude:
            continue
        if any(kw in f for kw in keywords):
            return i
    return None


def _column_map(datafields: list) -> dict:
    # 0=BIB, 1=ID, 2=rank/place column are constant across every RaceResult
    # list seen (rank's header is often a formula string like
    # "WithStatus([TotalRankp])" -- excluding it up front avoids "total"/"rank"
    # false-matching the Finish/split keywords below).
    used = {0, 1, 2}
    name_idx = _find_field(datafields, ["flname", "displayname", "firstname"], used)
    last_idx = None
    if name_idx is not None:
        used.add(name_idx)
        if "firstname" in datafields[name_idx].lower():
            last_idx = _find_field(datafields, ["lastname"], used)
            if last_idx is not None:
                used.add(last_idx)
    club_idx = _find_field(datafields, ["club", "atf2"], used)
    if club_idx is not None:
        used.add(club_idx)
    sex_idx = _find_field(datafields, ["sex", "malefemale", "gender"], used)
    if sex_idx is not None:
        used.add(sex_idx)
    ag_idx = _find_field(datafields, ["agegroup", "age group", "age_group"], used)
    if ag_idx is not None:
        used.add(ag_idx)
    year_idx = _find_field(datafields, ["year"], used)
    if year_idx is not None:
        used.add(year_idx)

    splits = {}
    for label, keywords in _SPLIT_KEYWORDS:
        idx = _find_field(datafields, keywords, used)
        if idx is not None:
            splits[label] = idx
            used.add(idx)

    return {
        "name_idx": name_idx, "last_idx": last_idx, "club_idx": club_idx,
        "sex_idx": sex_idx, "ag_idx": ag_idx, "year_idx": year_idx, "splits": splits,
    }


def _row_name(r: list, cols: dict, name_format: str) -> str:
    if cols["last_idx"] is not None:
        first = r[cols["name_idx"]] if cols["name_idx"] < len(r) else ""
        last = r[cols["last_idx"]] if cols["last_idx"] < len(r) else ""
        return f"{first} {last}".strip()
    if cols["name_idx"] is None or cols["name_idx"] >= len(r):
        return ""
    return format_name(r[cols["name_idx"]], name_format)


def _iter_rows(payload: dict, keep_prefixes: tuple[str, ...] | None):
    data = payload.get("data", {}) or {}
    for contest_key, group_val in data.items():
        if keep_prefixes and not any(contest_key.startswith(p) for p in keep_prefixes):
            continue
        if isinstance(group_val, dict):
            for _group_key, rows in group_val.items():
                for r in rows:
                    yield r
        elif isinstance(group_val, list):
            for r in group_val:
                yield r


@dataclass
class KerryGalwayRace:
    """One race. ``ag_list``/``ag_contest`` are set only for the "agejoin"
    style, where sex/year/club must come from a separate list keyed by
    RaceResult's internal ID (column 1 in every list seen).
    """
    event_id: str
    name: str
    processed_filename: str
    listname: str
    page: str = "results"
    contest: str | None = None          # param sent with the main-list request
    keep_prefixes: tuple = ()           # contest-key prefixes to keep, e.g. ("#1_",)
    race_year: int | None = None        # only needed when deriving band from YEAR
    ag_list: str | None = None
    ag_contest: str | None = None
    name_format: str = "plain"

    @property
    def raw_path(self) -> Path:
        return _RAW_DIR / f"{self.event_id}.json"

    @property
    def ag_raw_path(self) -> Path:
        return _RAW_DIR / f"{self.event_id}_ag.json"

    @property
    def processed_path(self) -> Path:
        return PROCESSED_DIR / self.processed_filename


def fetch_raw(race: KerryGalwayRace) -> None:
    client = RaceResultClient(race.event_id, page=race.page)
    payload = client.fetch_list(race.listname, contest=race.contest)
    race.raw_path.parent.mkdir(parents=True, exist_ok=True)
    race.raw_path.write_text(json.dumps(payload), encoding="utf-8")
    if race.ag_list:
        ag_payload = client.fetch_list(race.ag_list, contest=race.ag_contest)
        race.ag_raw_path.write_text(json.dumps(ag_payload), encoding="utf-8")


def _build_ag_map(payload: dict, keep_prefixes: tuple) -> dict:
    """id -> (sex, year, club) from an 'Age Group ... - Win' list."""
    datafields = payload.get("DataFields", []) or []
    cols = _column_map(datafields)
    out = {}
    for r in _iter_rows(payload, keep_prefixes):
        if len(r) <= 1:
            continue
        pid = r[1]
        sex = r[cols["sex_idx"]] if cols["sex_idx"] is not None and cols["sex_idx"] < len(r) else ""
        year = to_int(r[cols["year_idx"]]) if cols["year_idx"] is not None and cols["year_idx"] < len(r) else None
        club = r[cols["club_idx"]] if cols["club_idx"] is not None and cols["club_idx"] < len(r) else ""
        out[pid] = (sex, year, club)
    return out


def parse_race(race: KerryGalwayRace) -> pd.DataFrame:
    payload = json.loads(race.raw_path.read_text(encoding="utf-8"))
    datafields = payload.get("DataFields", []) or []
    cols = _column_map(datafields)
    splits = cols["splits"]

    ag_map = {}
    if race.ag_list:
        ag_payload = json.loads(race.ag_raw_path.read_text(encoding="utf-8"))
        ag_map = _build_ag_map(ag_payload, race.keep_prefixes)

    def split_val(r, label):
        idx = splits.get(label)
        return to_timedelta(r[idx]) if idx is not None and idx < len(r) else pd.NaT

    rows = []
    for r in _iter_rows(payload, race.keep_prefixes):
        pid = r[1] if len(r) > 1 else None
        sex = r[cols["sex_idx"]] if cols["sex_idx"] is not None and cols["sex_idx"] < len(r) else ""
        year = to_int(r[cols["year_idx"]]) if cols["year_idx"] is not None and cols["year_idx"] < len(r) else None
        club = r[cols["club_idx"]] if cols["club_idx"] is not None and cols["club_idx"] < len(r) else ""
        band = r[cols["ag_idx"]] if cols["ag_idx"] is not None and cols["ag_idx"] < len(r) else ""

        if not sex and pid in ag_map:
            ag_sex, ag_year, ag_club = ag_map[pid]
            sex = sex or ag_sex
            year = year or ag_year
            club = club or ag_club

        if not band and year and race.race_year:
            band = _band_from_age(race.race_year - year)

        rows.append({
            "Place": None,
            "Bib": to_int(r[0]) if len(r) > 0 else None,
            "Name": _row_name(r, cols, race.name_format),
            "Age_Group": (band or "").strip(),
            "Group_Rank": None,
            "Class": _class_from_sex(sex),
            "Club": (club or "").strip(),
            "Swim": split_val(r, "Swim"),
            "T1": split_val(r, "T1"),
            "Bike": split_val(r, "Bike"),
            "T2": split_val(r, "T2"),
            "Run": split_val(r, "Run"),
            "Finish": split_val(r, "Finish"),
        })

    df = pd.DataFrame(rows, columns=STANDARD_COLS)
    if df.empty:
        return df
    df = df.sort_values("Finish", na_position="last").reset_index(drop=True)
    df["Place"] = pd.Series(range(1, len(df) + 1), dtype="Int64").where(df["Finish"].notna())
    df["Group_Rank"] = df.groupby("Class")["Finish"].rank(method="min").astype("Int64")
    return df


def build_race(race: KerryGalwayRace) -> Path:
    fetch_raw(race)
    df = parse_race(race)
    return save_processed(df, race.processed_path)


def build_all(races: list[KerryGalwayRace]) -> dict:
    return {r.name: build_race(r) for r in races}
