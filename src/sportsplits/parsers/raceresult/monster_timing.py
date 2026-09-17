"""Monster Timing (monstertiming.ie) Irish triathlon races -- these are ordinary
my.raceresult.com events (Monster Timing uses RaceResult for its timing), but
with list conventions that don't fit the existing EventSpec/parse_event model
used for the app's other RaceResult events (Fastnet, Jailbreak, etc.):

* The place/rank column is a medal-icon SWITCH formula for the top 3
  ("[img:my\\medal_1.png|...]") even in otherwise-plain lists -- never a
  reliable place number to read directly, so Place is always derived here by
  ranking on Finish time instead.
* Class isn't a data column at all -- rows are nested by *group key*
  ("#1_Female Category", "#2_Open Category", or on some events just "Female"/
  "Open" without the "#N_.../Category" wrapping), and Class comes from there.
* Split-time values are sometimes plain ("00:09:03") and sometimes decorated
  with a rank suffix RaceResult appends ("00:44:54 (17th)") depending on how
  the organiser configured that particular event's list -- handled uniformly
  by stripping the suffix if present (a no-op on already-plain values).
* Age_Group is sometimes its own field, sometimes packed into a combined
  "Female 25-29"-style field, and sometimes absent from the list entirely.

Column identification is therefore done by matching each DataField's (lower-
cased) text against keywords, not by fixed position -- positions differ
between events depending on how many extra columns (nationality, team, etc.)
an organiser's template includes.

Discovery process (see monster_timing_manifest.py for the resulting event
list): walked monstertiming.ie/race-results/ for events tagged data-type=5
(Triathlon), extracted each event's embedded my.raceresult.com id from the
page's `new RRPublish(el, <id>, "results")` snippet, then inspected each
event's config (contests, published lists) directly via RaceResultClient.
Only 2025/2026 events exist in Monster Timing's results archive -- no 2024
triathlons were found (the year filter on their own site only offers
2025/2026, and guessed 2024 slugs all 404'd), so this is a real gap in the
source, not a scraping miss.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from sportsplits.config import RAW_DIR, PROCESSED_DIR
from sportsplits.parsers.raceresult.common import (
    RaceResultClient,
    STANDARD_COLS,
    to_timedelta,
    to_int,
    save_processed,
)

_MT_RAW_DIR = RAW_DIR / "monster_timing"

# "00:44:54 (17th)" -> "00:44:54"; a no-op (no match) on plain values.
_RANK_SUFFIX = re.compile(r"^\s*([\d:]+)\s*\(\d+\w*\)\s*$")

_SPLIT_KEYWORDS = [
    ("Swim", ["swim"]),
    ("T1", ["t1", "transition1", "trans1"]),
    ("Bike", ["bike", "cycle"]),
    ("T2", ["t2", "transition2", "trans2"]),
    ("Run", ["run"]),
    ("Finish", ["time", "finish", "finishresult"]),
]


@dataclass
class MonsterTimingRace:
    """One (event, contest) pair -- a single distance/category at a Monster
    Timing event. `needs_contest_param`: False for older accounts where the
    combined multi-contest response is filtered client-side by contest prefix
    instead (RaceResultClient.fetch_list(contest=None) still returns everything).
    """
    event_id: str
    contest: str
    name: str                  # registry / display name, e.g. "Lough Ree Monster Triathlon 2025 - Sprint"
    listname: str
    processed_filename: str
    needs_contest_param: bool = True

    @property
    def raw_path(self) -> Path:
        return _MT_RAW_DIR / f"{self.event_id}_{self.contest}.json"

    @property
    def processed_path(self) -> Path:
        return PROCESSED_DIR / self.processed_filename


def _clean_time(value):
    if not value:
        return pd.NaT
    m = _RANK_SUFFIX.match(value)
    return to_timedelta(m.group(1) if m else value)


def _clean_group_class(group_key: str) -> str:
    """"#2_Open Category" / "#1_Female" / "#1_Male" -> "Open" / "Female" / "Open"."""
    text = re.sub(r"^#\d+_", "", group_key or "").strip()
    text = re.sub(r"\s+Category$", "", text, flags=re.IGNORECASE).strip()
    return "Open" if text == "Male" else text


def _split_class_agegroup(text: str):
    """A combined field like "Female 25-29" -> ("Female", "25-29"). The class
    word isn't always first -- e.g. "Junior Open 17-19" -- so scan all tokens
    and keep the rest (including any prefix like "Junior") as the age group.
    """
    text = (text or "").strip()
    tokens = text.split()
    for i, t in enumerate(tokens):
        if t in ("Male", "Female", "Open"):
            cls = "Open" if t == "Male" else t
            return cls, " ".join(tokens[:i] + tokens[i + 1:]).strip()
    return "", text


def _find_field(datafields: list, keywords: list, exclude: set) -> int | None:
    low = [f.lower() for f in datafields]
    for i, f in enumerate(low):
        if i in exclude:
            continue
        if any(kw in f for kw in keywords):
            return i
    return None


def _column_map(datafields: list) -> dict:
    """Locate Name/Club/Age_Group/split columns by keyword match. Bib/ID are
    always the first two columns (consistent across every Monster Timing list
    checked); place/rank is never trusted (see module docstring)."""
    used = {0, 1}
    name_idx = _find_field(datafields, ["flname", "name"], used)
    if name_idx is not None:
        used.add(name_idx)
    club_idx = _find_field(datafields, ["club", "team"], used)
    if club_idx is not None:
        used.add(club_idx)
    # "category" alone is deliberately excluded: it false-matches unrelated
    # fields like "RaceCategoryOF" before reaching the real AGEGROUP.NAME field.
    ag_idx = _find_field(datafields, ["agegroup", "age group", "age_group"], used)
    if ag_idx is not None:
        used.add(ag_idx)

    splits = {}
    for label, keywords in _SPLIT_KEYWORDS:
        idx = _find_field(datafields, keywords, used)
        if idx is not None:
            splits[label] = idx
            used.add(idx)

    return {"name_idx": name_idx, "club_idx": club_idx, "ag_idx": ag_idx, "splits": splits}


def fetch_raw(race: MonsterTimingRace) -> dict:
    client = RaceResultClient(race.event_id)
    contest_param = race.contest if race.needs_contest_param else None
    payload = client.fetch_list(race.listname, contest=contest_param)
    race.raw_path.parent.mkdir(parents=True, exist_ok=True)
    race.raw_path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def _iter_rows(payload: dict, contest_filter: str | None):
    """Yield (group_key, row_values); group_key carries Class (see module
    docstring). Rows are read in the API's own order -- Place is derived
    separately by ranking on Finish, not from iteration order, since RaceResult
    groups (e.g. gender categories) are separate leaderboards, not one ranked list.
    """
    data = payload.get("data", {}) or {}
    for contest_key, group_val in data.items():
        if contest_filter and not contest_key.startswith(f"#{contest_filter}_"):
            continue
        if isinstance(group_val, dict):
            for group_key, rows in group_val.items():
                for r in rows:
                    yield group_key, r
        elif isinstance(group_val, list):
            for r in group_val:
                yield contest_key, r


def parse_payload(payload: dict, contest_filter: str | None = None) -> pd.DataFrame:
    datafields = payload.get("DataFields", []) or []
    cols = _column_map(datafields)
    splits = cols["splits"]

    rows = []
    for group_key, r in _iter_rows(payload, contest_filter):
        group_cls = _clean_group_class(group_key)

        raw_ag = ""
        if cols["ag_idx"] is not None and cols["ag_idx"] < len(r):
            raw_ag = r[cols["ag_idx"]] or ""

        # Prefer a class embedded in the age-group *field* over the group key:
        # some events (e.g. flat, non-gender-nested lists) put "Open 25-29" in
        # the field and a meaningless contest name in the group key. Failing
        # that, some events instead pack the class into the group key itself
        # ("Female 20-34" as the whole group, no separate age-group field).
        field_cls, field_ag = _split_class_agegroup(raw_ag)
        if field_cls:
            cls, age_group = field_cls, field_ag
        else:
            group_cls2, group_ag2 = _split_class_agegroup(group_cls)
            if group_cls2:
                cls, age_group = group_cls2, group_ag2
            else:
                cls, age_group = group_cls, raw_ag.strip()

        def split_val(label):
            idx = splits.get(label)
            return _clean_time(r[idx]) if idx is not None and idx < len(r) else pd.NaT

        rows.append({
            "Place": None,  # filled in below by ranking on Finish
            "Bib": to_int(r[0]) if len(r) > 0 else None,
            "Name": (r[cols["name_idx"]] or "").strip() if cols["name_idx"] is not None and cols["name_idx"] < len(r) else "",
            "Age_Group": age_group,
            "Group_Rank": None,
            "Class": cls,
            "Club": (r[cols["club_idx"]] or "").strip() if cols["club_idx"] is not None and cols["club_idx"] < len(r) else "",
            "Swim": split_val("Swim"),
            "T1": split_val("T1"),
            "Bike": split_val("Bike"),
            "T2": split_val("T2"),
            "Run": split_val("Run"),
            "Finish": split_val("Finish"),
        })

    df = pd.DataFrame(rows, columns=STANDARD_COLS)
    if df.empty:
        return df

    df = df.sort_values("Finish", na_position="last").reset_index(drop=True)
    df["Place"] = pd.Series(range(1, len(df) + 1), dtype="Int64").where(df["Finish"].notna())
    # Group_Rank: rank within Class, same ordering.
    df["Group_Rank"] = (
        df.groupby("Class")["Finish"].rank(method="min").astype("Int64")
        if not df.empty else df["Group_Rank"]
    )
    return df


def process_event(race: MonsterTimingRace) -> Path:
    payload = json.loads(race.raw_path.read_text(encoding="utf-8"))
    contest_filter = race.contest if not race.needs_contest_param else None
    df = parse_payload(payload, contest_filter)
    return save_processed(df, race.processed_path)


def build_race(race: MonsterTimingRace) -> Path:
    fetch_raw(race)
    return process_event(race)
