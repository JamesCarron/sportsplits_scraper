"""Small one-off/club-run Irish triathlons found directly in my.raceresult.com's
public event directory (via RaceResultClient.search_events) during the
Triathlon-Ireland gap-analysis sweep. Unlike the app's other RaceResult events
(Fastnet, Jailbreak, etc. -- fixed EventSpec column positions) these vary too
much event-to-event to use EventSpec: some publish a "Full Results" list with
FLNAME already "First Last", some only keep FIRSTNAME/LASTNAME split on their
live "Presenter/Announcer|TV Screen" or "DJ Spotter" screens (which, unlike
Monster Timing's equivalent lists, several of these small accounts do leave
populated after the event ends -- checked individually per event), and some
publish only an age-group-banded Finish time with no splits at all (Sheephaven).

Column identification is therefore done by matching each DataField's (lower-
cased) text against keywords, same technique as monster_timing.py, and Place
is always derived by ranking on Finish (never trusted from a rank column,
which is sometimes a plain "1." string and sometimes a medal-icon formula).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
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

_RAW_DIR = RAW_DIR / "rr_small_races"

_SPLIT_KEYWORDS = [
    ("Swim", ["swim"]),
    ("T1", ["t1", "transition1", "trans1"]),
    ("Bike", ["bike", "cycle"]),
    ("T2", ["t2", "transition2", "trans2"]),
    ("Run", ["run"]),
    ("Finish", ["time", "finish", "total"]),
]


@dataclass
class SmallRace:
    """One event's chosen results list. ``contests``: contest ids to fetch and
    merge (each small account only ever exposed a single contest during this
    sweep, but the field stays a tuple for consistency); () means fetch with no
    contest param at all (works for single-contest "Full Results"-style lists).
    ``finish_only``: True when the list carries only a banded Finish time, no
    splits (Sheephaven's public archive -- confirmed no splits exist anywhere
    on that event, not a parsing gap).
    """
    event_id: str
    name: str
    listname: str
    processed_filename: str
    contests: tuple = ("1",)
    finish_only: bool = False

    @property
    def raw_path(self) -> Path:
        return _RAW_DIR / f"{self.event_id}.json"

    @property
    def processed_path(self) -> Path:
        return PROCESSED_DIR / self.processed_filename


def _find_field(datafields: list, keywords: list, exclude: set) -> int | None:
    low = [f.lower() for f in datafields]
    for i, f in enumerate(low):
        if i in exclude:
            continue
        if any(kw in f for kw in keywords):
            return i
    return None


def _column_map(datafields: list) -> dict:
    # Rank/place formula columns (e.g. "WithStatus([TotalRankp])") often embed
    # a split-time keyword like "total" -- exclude them upfront so they never
    # shadow the real time field later in the list. The first one found is also
    # kept (not just excluded) as the DNF/DNS/DSQ status indicator: RaceResult's
    # "WithStatus(...)" wrapper puts the athlete's status string there instead
    # of a rank number whenever they didn't finish, and a DNF's "Total" is a
    # partial split at the point of withdrawal, not a real finish time.
    rank_positions = [i for i, f in enumerate(datafields) if "rank" in f.lower()]
    used = {0, 1} | set(rank_positions)
    status_idx = rank_positions[0] if rank_positions else None
    first_idx = _find_field(datafields, ["firstname"], used)
    last_idx = _find_field(datafields, ["lastname"], used)
    if first_idx is not None:
        used.add(first_idx)
    if last_idx is not None:
        used.add(last_idx)

    name_idx = None
    if first_idx is None:
        # Tiered so a coincidental "name" substring elsewhere (e.g. a
        # "CONTEST.NAME" field) never wins over the real identity column.
        for kws in (["flname"], ["fullname", "displayname"], ["name"]):
            name_idx = _find_field(datafields, kws, used)
            if name_idx is not None:
                used.add(name_idx)
                break

    sex_idx = _find_field(datafields, ["sex", "gender"], used)
    if sex_idx is not None:
        used.add(sex_idx)
    club_idx = _find_field(datafields, ["club", "atf2", "team"], used)
    if club_idx is not None:
        used.add(club_idx)
    ag_idx = _find_field(datafields, ["agegroup", "age group", "age_group"], used)
    if ag_idx is not None:
        used.add(ag_idx)

    splits = {}
    for label, keywords in _SPLIT_KEYWORDS:
        idx = _find_field(datafields, keywords, used)
        if idx is not None:
            splits[label] = idx
            used.add(idx)

    return {
        "first_idx": first_idx, "last_idx": last_idx, "name_idx": name_idx,
        "sex_idx": sex_idx, "club_idx": club_idx, "ag_idx": ag_idx, "splits": splits,
        "status_idx": status_idx,
    }


def fetch_raw(race: SmallRace) -> dict:
    """Fetch every listed contest and merge into one payload (shared DataFields,
    unioned data). Idempotent -- overwrites the raw JSON each time. A response's
    top-level "data" is a dict keyed by contest (the common case) unless the
    event has exactly one contest and no age-group nesting, in which case
    RaceResult flattens it straight to a list of rows -- tagged under the
    requested contest id (or "_" when no contest param was used) so two such
    single-contest fetches merged together don't collide.
    """
    client = RaceResultClient(race.event_id)
    combined = {"DataFields": None, "data": {}}
    for contest in (race.contests or (None,)):
        payload = client.fetch_list(race.listname, contest=contest)
        if combined["DataFields"] is None:
            combined["DataFields"] = payload.get("DataFields", [])
        data = payload.get("data")
        if isinstance(data, dict):
            combined["data"].update(data)
        elif isinstance(data, list):
            combined["data"][f"_{contest or '_'}"] = data
    race.raw_path.parent.mkdir(parents=True, exist_ok=True)
    race.raw_path.write_text(json.dumps(combined), encoding="utf-8")
    return combined


def _iter_rows(payload: dict):
    """Yield (group_key, row). group_key is the innermost nesting key -- often
    meaningless, but on lists with no dedicated age-group column (Sheephaven's
    only published list) it *is* the age band ("#1_F25-29"), so it's always
    threaded through rather than discarded.
    """
    data = payload.get("data", {}) or {}
    for k1, v1 in data.items():
        if isinstance(v1, dict):
            for k2, rows in v1.items():
                for r in rows:
                    yield k2, r
        elif isinstance(v1, list):
            for r in v1:
                yield k1, r


def _group_key_to_band(group_key: str) -> str:
    """"#1_F25-29" -> "F25-29"; a no-op on keys with no "#N_" wrapper."""
    return re.sub(r"^#\d+_", "", group_key or "").strip()


_DNF_TOKENS = {"dnf", "dns", "dsq", "dq", "otl", "abs"}


def parse_payload(payload: dict) -> pd.DataFrame:
    datafields = payload.get("DataFields") or []
    cols = _column_map(datafields)
    splits = cols["splits"]

    def get(r, idx):
        return r[idx] if idx is not None and idx < len(r) else ""

    rows = []
    for group_key, r in _iter_rows(payload):
        status = (get(r, cols["status_idx"]) or "").strip().lower().rstrip(".")
        did_not_finish = status in _DNF_TOKENS

        if cols["first_idx"] is not None:
            name = f"{get(r, cols['first_idx'])} {get(r, cols['last_idx'])}".strip()
        else:
            name = (get(r, cols["name_idx"]) or "").strip()
        sex = (get(r, cols["sex_idx"]) or "").strip().lower()
        cls = {"m": "Open", "f": "Female"}.get(sex, "")
        if cols["ag_idx"] is not None:
            age_group = (get(r, cols["ag_idx"]) or "").strip()
        else:
            age_group = _group_key_to_band(group_key)

        def split_val(label):
            # A DNF/DNS/DSQ's recorded times are partial splits at the point of
            # withdrawal (or blank), never a completed performance -- excluded
            # from every split, not just Finish, so they can't leak into any
            # split-based stat either.
            if did_not_finish:
                return pd.NaT
            idx = splits.get(label)
            return to_timedelta(get(r, idx)) if idx is not None else pd.NaT

        rows.append({
            "Place": None,  # filled in below by ranking on Finish
            "Bib": to_int(r[0]) if len(r) > 0 else None,
            "Name": name,
            "Age_Group": age_group,
            "Group_Rank": None,
            "Class": cls,
            "Club": (get(r, cols["club_idx"]) or "").strip(),
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
    df["Group_Rank"] = df.groupby("Class")["Finish"].rank(method="min").astype("Int64")
    return df


def process_race(race: SmallRace) -> Path:
    payload = json.loads(race.raw_path.read_text(encoding="utf-8"))
    df = parse_payload(payload)
    return save_processed(df, race.processed_path)


def build_race(race: SmallRace) -> Path:
    fetch_raw(race)
    return process_race(race)


def build_all(races: list) -> dict:
    return {r.name: build_race(r) for r in races}
