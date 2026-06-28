"""RaceResult event definitions -- the single source of truth for which races
the app knows about and how each one's raw columns map to the standard format.

Two sources are combined by ``all_events()``:

* ``BUILTIN_EVENTS`` -- hand-tuned specs checked into the repo below.
* user events -- added at runtime (e.g. from the web UI via ``add_event``) and
  persisted to ``data/user_events.json`` so they survive a restart.

To add a built-in race by hand: drop a new EventSpec in BUILTIN_EVENTS (the column
layout can be discovered by opening the results URL and inspecting the list's
DataFields). races.py builds its REGISTRY straight from ``all_events()``, so a race
is registered exactly once and adding one is the only change needed.
"""
import json
from dataclasses import asdict, fields as _dc_fields

from sportsplits.config import DATA_DIR
from sportsplits.parsers.raceresult.common import (
    EventSpec,
    build_event,
    infer_event_spec,
    process_event,
    scrape_event,
)

# Layout notes (positions are indexes into each list row's DataFields):
#
# Fastnet 2025 (343797) "Full Results":
#   BIB, ID, place, FLNAME(plain), SEX(m/f), AGEGROUP(inline band), Club, 6 splits
#   -> three contests in one list; keep only the individual Sprint (#1_).
# Fastnet 2026 (402195) "Online|Final":
#   BIB, ID, place, DisplayName(Last,First), GenderTI(Open/Female), YEAR, CLUB, 6 splits
#   -> age-group band comes from the AG list; one known identity mix-up.
# Jailbreak 2026 (403737) "Online|Final":
#   BIB, ID, place, DisplayName(Last,First), YEAR, GenderTI(Open/Female), CLUB, 6 splits
#   -> like 2026 Fastnet but YEAR/Gender are swapped, so Class sits at index 5.

_AG_WIN_LIST = "Result Lists|Age Group Results - Win"

BUILTIN_EVENTS = [
    EventSpec(
        event_id="343797",
        name="Fastnet Sprint 2025",
        processed_filename="Fastnet_Sprint_Triathlon_2025.csv",
        main_list="Result Lists|Full Results",
        ag_list=_AG_WIN_LIST,
        name_format="plain",
        class_idx=4,
        class_map={"m": "Open", "f": "Female"},
        agegroup_idx=5,                 # band is inline; AG list supplies only the rank
        main_contest_prefix="#1_",      # individual Sprint only
    ),
    EventSpec(
        event_id="402195",
        name="Fastnet Sprint 2026",
        processed_filename="Fastnet_Sprint_Triathlon_2026.csv",
        main_list="Online|Final",
        ag_list=_AG_WIN_LIST,
        name_format="lastfirst",
        class_idx=4,
        identity_swaps=(("Patrick O'Connell", "James Carron"),),
    ),
    EventSpec(
        event_id="403737",
        name="Jailbreak 2026",
        processed_filename="Jailbreak_2026.csv",
        main_list="Online|Final",
        ag_list=_AG_WIN_LIST,
        name_format="lastfirst",
        class_idx=5,                    # YEAR and Gender are swapped vs. 2026 Fastnet
    ),
]

# Guard against accidental duplicate built-in names.
_names = [e.name for e in BUILTIN_EVENTS]
assert len(_names) == len(set(_names)), f"Duplicate event names in BUILTIN_EVENTS: {_names}"


# ──────────────────────────────────────────────────────────────────────────────
# User events (added at runtime, persisted to data/user_events.json)
# ──────────────────────────────────────────────────────────────────────────────
USER_EVENTS_PATH = DATA_DIR / "user_events.json"

_SPEC_FIELDS = {f.name for f in _dc_fields(EventSpec)}


def _spec_to_dict(spec: EventSpec) -> dict:
    return asdict(spec)  # tuples become lists; restored on load


def _spec_from_dict(d: dict) -> EventSpec:
    d = {k: v for k, v in d.items() if k in _SPEC_FIELDS}
    if "split_idx" in d:
        d["split_idx"] = tuple(d["split_idx"])
    if "identity_swaps" in d:
        d["identity_swaps"] = tuple(tuple(s) for s in d["identity_swaps"])
    return EventSpec(**d)


def load_user_events() -> list:
    if not USER_EVENTS_PATH.exists():
        return []
    data = json.loads(USER_EVENTS_PATH.read_text(encoding="utf-8"))
    return [_spec_from_dict(d) for d in data]


def _save_user_events(specs: list) -> None:
    USER_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USER_EVENTS_PATH.write_text(
        json.dumps([_spec_to_dict(s) for s in specs], indent=2), encoding="utf-8"
    )


def all_events() -> list:
    """Built-in events plus any user-added events (the live, complete set)."""
    return BUILTIN_EVENTS + load_user_events()


def add_event(url: str, name: str) -> EventSpec:
    """Auto-detect, scrape, process and persist a new RaceResult event.

    Returns the created EventSpec. Raises ValueError on a duplicate name or if the
    URL can't be turned into a results list.
    """
    name = name.strip()
    if not name:
        raise ValueError("A race name is required.")
    if name in {e.name for e in all_events()}:
        raise ValueError(f"A race named {name!r} already exists.")

    spec = infer_event_spec(url, name)
    build_event(spec)  # scrape -> data/raw, process -> data/processed (idempotent)

    user = load_user_events()
    user.append(spec)
    _save_user_events(user)
    return spec


# Snapshot used by races.py / the notebook at import time.
EVENTS = all_events()


def build_all() -> dict:
    """Scrape + process every event. Returns {name: processed_csv_path}."""
    return {spec.name: build_event(spec) for spec in all_events()}


def scrape_all() -> None:
    for spec in all_events():
        scrape_event(spec)


def process_all() -> dict:
    return {spec.name: process_event(spec) for spec in all_events()}
