"""Standalone RaceResult-powered Irish club triathlons/duathlons found via the
public my.raceresult.com event search -- not part of the Monster Timing account,
mostly timed by the small independent Irish outfit "JustRuns Events"
(www.justrunsevents.ie). Cork/Munster/Clare/Kerry sweep, 2024-2026.

Every EventSpec here is built with infer_event_spec(), the same auto-detection
the app's own "Add a race from my.raceresult.com" UI feature uses -- these are
ordinary single-account RaceResult events, no sharding/contest-param quirks
like Monster Timing needed.
"""
import re

import pandas as pd

from sportsplits.parsers.raceresult.common import (
    EventSpec, RaceResultClient, infer_event_spec, infer_field_mapping, slugify,
    _pick_main_list, _pick_ag_list, build_event, load_processed_csv, save_processed,
    _load_raw, to_int, _META_COLS,
)


def _infer_with_contest(url: str, name: str, processed_filename: str, contest: str) -> EventSpec:
    """Like infer_event_spec(), but probes the main list with an explicit
    ``contest`` param -- some accounts (e.g. this event's) 404 on a plain
    unscoped list fetch, the same quirk Monster Timing needed EventSpec.contest
    for. infer_event_spec() itself has no way to pass this through since the
    404 happens during its own internal probe, before a spec exists to carry it.
    """
    m = re.search(r"(\d{4,})", str(url))
    event_id = m.group(1)
    client = RaceResultClient(event_id)
    names = client.list_names()
    main_list = _pick_main_list(names)
    ag_list = _pick_ag_list(names)
    payload = client.fetch_list(main_list, contest=contest)
    datafields = payload.get("DataFields", []) or []
    return EventSpec(
        event_id=event_id, name=name, processed_filename=processed_filename,
        main_list=main_list, ag_list=ag_list, contest=contest,
        **infer_field_mapping(datafields),
    )


RACES: list[EventSpec] = [
    # Moby Dick Sprint 2024 (Youghal, Cork) -- South Coast Triathlon Club.
    # Data quirk: this event's inline "Swim" field is a wall-clock time-of-day,
    # not a duration (an artefact of this smaller meet's timing setup) -- so the
    # per-athlete Swim column is bogus (e.g. "13:41:02"). Finish is unaffected,
    # it comes from the separate TIME field. Not worth a special-case fix since
    # nothing downstream (the Ireland age-group tab) uses per-split times.
    _infer_with_contest("https://my.raceresult.com/308146/", "Moby Dick Sprint 2024",
                         "JR_MobyDick_2024.csv", contest="1"),
    # Brian Boru Triathlon 2026 (Killaloe, Clare) -- Boru Tri Club. Despite the
    # "2026" name this already ran (2026-06-06), well before today.
    infer_event_spec("https://my.raceresult.com/402365/", "Brian Boru Triathlon 2026",
                      "JR_BrianBoru_2026.csv"),
    # Ballybunion Duathlon 2025 (Kerry) -- Ballybunion Triathlon Club. No swim
    # leg (duathlon): the inline "Start" field (mapped to the Swim column by the
    # generic 6-of-last-columns split inference) is actually the first run leg,
    # not a swim -- mislabelled but harmless, since nothing downstream reads
    # per-split times for this dataset either.
    infer_event_spec("https://my.raceresult.com/345440/", "Ballybunion Duathlon 2025",
                      "JR_Ballybunion_2025.csv"),
]

# Moby Dick and Brian Boru's combined list carries relay teams and a youth race
# in the same response; keep only the individual adult distance (contest #1).
RACES[0].main_contest_prefix = "#1_"
RACES[1].main_contest_prefix = "#1_"

_BRIAN_BORU = RACES[1]
_BALLYBUNION = RACES[2]


def _ballybunion_gender_by_bib(spec: EventSpec) -> dict:
    """Ballybunion's list carries gender only in the nested group key
    ('#1_Female' / '#2_Male'), not a DataField -- infer_event_spec's generic
    class_idx auto-detection has nothing to find there (it falls back to the
    blank 'NATION.FLAG' column), so Class comes out empty for every row.
    Rebuild {bib: Class} straight from the raw list's group keys instead.
    """
    out = {}
    for _contest, group, *values in _load_raw(spec.raw_path(spec.main_list)):
        bib = to_int(values[spec.bib_idx])
        label = group.split("_", 1)[1] if "_" in group else group
        out[bib] = {"Female": "Female", "Male": "Open"}.get(label, label)
    return out


def _field_idx(spec: EventSpec, field_name: str) -> int:
    """Position of a named DataField within a raw row's *values (post contest/
    group unpacking) -- re-derived from the raw CSV's own header, since
    EventSpec only keeps the handful of positions infer_field_mapping cared
    about, not every field."""
    header = pd.read_csv(spec.raw_path(spec.main_list), dtype=str, nrows=0).columns.tolist()
    return header.index(field_name) - len(_META_COLS)


def _ageband_by_bib(spec: EventSpec, race_year: int) -> dict:
    """Bucket each athlete's birth YEAR into the same genuine 5-year bands used
    everywhere else in this app (age = race_year - birth_year, on-Dec-31-of-
    race-year convention). Used for two different reasons per event:

    - Ballybunion publishes no age-group list at all (single combined list, no
      banding), so this is the only source of any band.
    - Brian Boru's own ag_list bands are wide non-standard buckets (16-34,
      35-49, 50+, gender-prefixed "O"/"F" instead of "M"/"F"). analytics.py's
      _BAND_RE (deliberately) requires only a digit-digit shape, not band
      *width* or canonical membership, and its gender-prefix-strip regex only
      strips a literal M/F -- so "F16-34"/"F35-49" survive it verbatim (their
      "F" is a real M/F prefix) while "O16-34"/"O35-49" don't (Brian Boru's
      "O" isn't M/F) -- inconsistent, silently double-counting Female athletes
      into two extra bogus bands while every Male athlete's non-standard band
      is correctly dropped. Recomputing real bands from YEAR for every row
      sidesteps analytics.py's regex quirk entirely rather than relying on it.
    """
    year_idx = _field_idx(spec, "YEAR")
    out = {}
    for _contest, _group, *values in _load_raw(spec.raw_path(spec.main_list)):
        bib = to_int(values[spec.bib_idx])
        year = to_int(values[year_idx])
        if bib is None or year is None:
            continue
        age = race_year - year
        if age < 18 or age > 84:
            continue
        lo = 18 if age <= 24 else (age // 5) * 5
        out[bib] = "18-24" if age <= 24 else f"{lo}-{lo + 4}"
    return out


def build_all() -> dict:
    """Scrape + process every race, fix Ballybunion's Class column and both
    Ballybunion's and Brian Boru's Age_Group column (see docstrings above),
    return {name: processed_path}."""
    for spec in RACES:
        build_event(spec)

    df = load_processed_csv(_BALLYBUNION.processed_path)
    df["Class"] = df["Bib"].map(_ballybunion_gender_by_bib(_BALLYBUNION))
    df["Age_Group"] = df["Bib"].map(_ageband_by_bib(_BALLYBUNION, 2025)).fillna("")
    save_processed(df, _BALLYBUNION.processed_path)

    df = load_processed_csv(_BRIAN_BORU.processed_path)
    df["Age_Group"] = df["Bib"].map(_ageband_by_bib(_BRIAN_BORU, 2026)).fillna("")
    save_processed(df, _BRIAN_BORU.processed_path)

    return {spec.name: spec.processed_path for spec in RACES}
