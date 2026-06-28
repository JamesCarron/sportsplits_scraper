from sportsplits.config import RAW_DIR
from sportsplits.parsers.clonmel import load_final as _load_clonmel_final, load_draft as _load_clonmel_draft
from sportsplits.parsers.lost_sheep import load_results as _load_lost_sheep
from sportsplits.parsers.raceresult.common import load_processed_csv
from sportsplits.parsers.raceresult.events import EVENTS, add_event
from sportsplits.metrics import build_metrics_from_df

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


def load_all() -> dict:
    """Load and compute metrics for every registered race. Returns {name: df}."""
    result = {}
    for name, (path, loader) in REGISTRY.items():
        raw = loader(path)
        result[name] = build_metrics_from_df(raw)
    return result


def add_race_from_url(url: str, name: str, race_dfs: dict):
    """Scrape a new RaceResult event, register it, and load it into ``race_dfs``.

    Used by the web UI: auto-detects the event layout, writes its raw/processed
    CSVs, persists it to data/user_events.json (so it survives a restart), updates
    the in-memory REGISTRY and the live ``race_dfs`` dict, and returns the
    metrics-augmented DataFrame for the new race.
    """
    name = (name or "").strip()
    if name in race_dfs:
        raise ValueError(f"A race named {name!r} already exists.")

    spec = add_event(url, name)
    df = build_metrics_from_df(load_processed_csv(spec.processed_path))
    REGISTRY[spec.name] = (spec.processed_path, load_processed_csv)
    race_dfs[spec.name] = df
    return df
