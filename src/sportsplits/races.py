import json

from sportsplits.config import RAW_DIR
from sportsplits.parsers.clonmel import load_final as _load_clonmel_final, load_draft as _load_clonmel_draft
from sportsplits.parsers.lost_sheep import load_results as _load_lost_sheep
from sportsplits.parsers.raceresult.common import load_processed_csv
from sportsplits.parsers.raceresult.events import EVENTS, add_event
from sportsplits.parsers.ironman.common import records_to_df
from sportsplits.parsers.ironman.events import EVENTS as IRONMAN_EVENTS
from sportsplits.parsers.ironman.regular_races_manifest import FULL_RACES as _REG_FULL, HALF_RACES as _REG_HALF
from sportsplits.metrics import build_metrics_from_df

_REGULAR_RAW_DIR = RAW_DIR / "ironman_regular"


def _load_regular_race(path):
    return records_to_df(json.loads(path.read_text(encoding="utf-8")))


# Registry: display name → (file path, loader function).
# Loaders must return a DataFrame in the standard 13-column format (data_format.md).
#
# File-based races read their source files directly from data/raw/ (they have no
# separate processed artifact). RaceResult URL races are generated from the EVENTS
# spec and read their app-ready CSV from data/processed/ — so adding a race there
# is the only change needed, and a name can never be registered twice.
REGISTRY = {
    'Clonmel 2026_DRAFT': (RAW_DIR / 'Clonmel_Camida_2026_DRAFT.txt', _load_clonmel_draft),
    'Clonmel 2026':       (RAW_DIR / 'Clonmel_Camida_2026.txt',        _load_clonmel_final),
    'Lost Sheep 2025':    (RAW_DIR / 'CTC_Lost_Sheep_2025.csv',         _load_lost_sheep),
}

for _spec in EVENTS:
    REGISTRY[_spec.name] = (_spec.processed_path, load_processed_csv)

for _spec in IRONMAN_EVENTS:
    REGISTRY[_spec.name] = (_spec.processed_path, load_processed_csv)

# Regular (non-championship) Ironman races, 2025-2026 -- previously only used
# in aggregate by the Age-Group Analysis page's "Ironman" tab, not individually
# selectable here. Named "<venue> <year>" (e.g. "Ironman Arizona 2025"), which
# never collides with the "IM WC ..."/"IM 70.3 WC ..." naming the championship
# races use.
for _race_id, _name, _year in _REG_FULL + _REG_HALF:
    REGISTRY[f'{_name} {_year}'] = (_REGULAR_RAW_DIR / f'{_race_id}.json', _load_regular_race)

# Race names, grouped for the UI's collection filter. Built as a function (not a
# module-level snapshot) so it reflects races added at runtime via the "Add a race"
# form -- anything not a built-in Ironman race falls into 'My Races'.
_IRONMAN_FULL_NAMES = {e.name for e in IRONMAN_EVENTS if e.distance == 'full'}
_IRONMAN_703_NAMES = {e.name for e in IRONMAN_EVENTS if e.distance == '70.3'}
_IRONMAN_REG_FULL_NAMES = {f'{name} {year}' for _, name, year in _REG_FULL}
_IRONMAN_REG_703_NAMES = {f'{name} {year}' for _, name, year in _REG_HALF}
_ALL_BUILTIN_IRONMAN_NAMES = _IRONMAN_FULL_NAMES | _IRONMAN_703_NAMES | _IRONMAN_REG_FULL_NAMES | _IRONMAN_REG_703_NAMES

# Registered (selectable, appear in collections/dropdown) but NOT eagerly
# loaded by load_all() -- parsing all 251 of these upfront added 80+ seconds
# to app startup for races most sessions never look at. get_race_df() below
# loads + caches one into race_dfs on first selection instead.
_LAZY_LOAD_NAMES = _IRONMAN_REG_FULL_NAMES | _IRONMAN_REG_703_NAMES


def race_collections(race_names) -> dict:
    """{collection label: [race names]} for the given (live) set of race names."""
    race_names = list(race_names)
    my_races = [n for n in race_names if n not in _ALL_BUILTIN_IRONMAN_NAMES]
    return {
        'All Races': race_names,
        'My Races': my_races,
        'Ironman World Championship': [n for n in race_names if n in _IRONMAN_FULL_NAMES],
        'Ironman 70.3 World Championship': [n for n in race_names if n in _IRONMAN_703_NAMES],
        'Ironman (regular, full)': [n for n in race_names if n in _IRONMAN_REG_FULL_NAMES],
        'Ironman (regular, 70.3)': [n for n in race_names if n in _IRONMAN_REG_703_NAMES],
    }


def load_all() -> dict:
    """Load and compute metrics for every registered race except the lazy
    ones (see _LAZY_LOAD_NAMES). Returns {name: df}."""
    result = {}
    for name, (path, loader) in REGISTRY.items():
        if name in _LAZY_LOAD_NAMES:
            continue
        raw = loader(path)
        result[name] = build_metrics_from_df(raw)
    return result


def get_race_df(race_dfs: dict, race_name: str):
    """race_dfs[race_name], loading + caching it first if this is a lazy
    race's (see _LAZY_LOAD_NAMES) first selection. Every other race is
    already in race_dfs from load_all() at startup, so this is a plain dict
    lookup for them."""
    if race_name not in race_dfs:
        path, loader = REGISTRY[race_name]
        race_dfs[race_name] = build_metrics_from_df(loader(path))
    return race_dfs[race_name]


def add_race_from_url(url: str, name: str, race_dfs: dict):
    """Scrape a new RaceResult event, register it, and load it into ``race_dfs``.

    Used by the web UI: auto-detects the event layout, writes its raw/processed
    CSVs, persists it to data/user_events.json (so it survives a restart), updates
    the in-memory REGISTRY and the live ``race_dfs`` dict, and returns the
    metrics-augmented DataFrame for the new race.
    """
    name = (name or "").strip()
    if name in REGISTRY:
        raise ValueError(f"A race named {name!r} already exists.")

    spec = add_event(url, name)
    df = build_metrics_from_df(load_processed_csv(spec.processed_path))
    REGISTRY[spec.name] = (spec.processed_path, load_processed_csv)
    race_dfs[spec.name] = df
    return df
