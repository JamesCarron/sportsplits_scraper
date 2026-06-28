"""RaceResult event definitions -- the single source of truth for which races
the app knows about and how each one's raw columns map to the standard format.

To add a race: drop a new EventSpec in EVENTS below (the column layout can be
discovered by opening the results URL and inspecting the list's DataFields), then
re-run scrape_and_process.ipynb. races.py builds its REGISTRY straight from this
list, so nothing else needs editing and a name can never be registered twice.
"""
from sportsplits.parsers.raceresult.common import EventSpec, build_event, scrape_event, process_event

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

EVENTS = [
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

# Guard against accidental duplicate registry names.
_names = [e.name for e in EVENTS]
assert len(_names) == len(set(_names)), f"Duplicate event names in EVENTS: {_names}"


def build_all() -> dict:
    """Scrape + process every event. Returns {name: processed_csv_path}."""
    return {spec.name: build_event(spec) for spec in EVENTS}


def scrape_all() -> None:
    for spec in EVENTS:
        scrape_event(spec)


def process_all() -> dict:
    return {spec.name: process_event(spec) for spec in EVENTS}
