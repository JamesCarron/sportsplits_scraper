"""Shared engine for RaceResult (my.raceresult.com) events.

Two clearly-separated stages, so a refreshed scrape never mixes fetching with
interpretation:

1. SCRAPE (``scrape_event`` / ``scrape_url``) -- talk to the RaceResult
   "RRPublish" JSON API and dump each requested list to a *raw* CSV with no
   interpretation: times stay as strings, names stay as "Last, First", the
   place keeps its trailing dot, and the API's own ``DataFields`` are the
   headers. The contest/age-group grouping keys are preserved in two leading
   ``__contest__`` / ``__group__`` columns. Re-running overwrites the raw file,
   so pulling again never duplicates rows.

2. PROCESS (``process_event``) -- read the raw CSV(s) for one event and emit a
   *processed* CSV in the standard 13-column format described in data_format.md
   (Place, Bib, Name, Age_Group, Group_Rank, Class, Club + 6 splits), with
   readable time strings and "First Last" names. Per-event differences (column
   positions, name order, class derivation, where the age-group band comes from)
   live entirely in an ``EventSpec``; this module stays event-agnostic.

The app's metrics (the extra 24 percentile columns) are still computed at load
time by metrics.build_metrics_from_df, so they are never baked into the CSV and
can never go stale -- see races.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import requests

# Processed CSVs live in the race_results/ folder (one level up from parsers/);
# raw dumps go in a raw/ subfolder beside them.
DATA_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = DATA_DIR / "raw"

SPLIT_COLS = ["Swim", "T1", "Bike", "T2", "Run", "Finish"]
STANDARD_COLS = ["Place", "Bib", "Name", "Age_Group", "Group_Rank", "Class", "Club", *SPLIT_COLS]

_META_COLS = ["__contest__", "__group__"]
_HEADERS = {"User-Agent": "Mozilla/5.0"}


# ──────────────────────────────────────────────────────────────────────────────
# Event configuration
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class EventSpec:
    """Everything that varies between RaceResult events.

    All ``*_idx`` values are positions within a list row's ``DataFields`` (the
    grouping keys are handled separately). The defaults match the common
    triathlon layout (BIB, ID, place, name, class, year/club, 6 splits); only
    the columns that actually move need to be overridden per event.
    """
    event_id: str
    name: str                                  # registry / display name
    processed_filename: str                    # output CSV name in race_results/
    main_list: str                             # RaceResult list with per-athlete results
    ag_list: str | None = None                 # age-group list (band and/or rank), or None

    # Column positions within the main list's data fields.
    place_idx: int = 2
    bib_idx: int = 0
    id_idx: int = 1
    name_idx: int = 3
    name_format: str = "lastfirst"             # "lastfirst" (reorder) | "plain"
    class_idx: int = 4
    class_map: dict | None = None              # e.g. {"m": "Open", "f": "Female"}; None = use raw
    club_idx: int = 6
    agegroup_idx: int | None = None            # inline band column; None = take band from ag_list
    split_idx: tuple = (7, 8, 9, 10, 11, 12)   # Swim, T1, Bike, T2, Run, Finish

    # Some lists carry several contests; keep only groups with this prefix
    # ("" = keep all). e.g. "#1_" for the individual race only.
    main_contest_prefix: str = ""

    # Column positions within the age-group list's data fields.
    ag_id_idx: int = 1
    ag_rank_idx: int = 2

    # Source data-entry errors: athlete pairs whose identities were attached to
    # each other's timing rows. Identity fields are swapped back during process.
    identity_swaps: tuple = ()

    @property
    def processed_path(self) -> Path:
        return DATA_DIR / self.processed_filename

    @property
    def registry_path(self) -> str:
        """Relative path the app's REGISTRY uses to load the processed CSV."""
        return f"race_results/{self.processed_filename}"

    def raw_path(self, listname: str) -> Path:
        return raw_path(self.event_id, listname)


# ──────────────────────────────────────────────────────────────────────────────
# Value helpers (shared by every event)
# ──────────────────────────────────────────────────────────────────────────────
def to_timedelta(t) -> pd.Timedelta:
    """Convert an 'M:SS' or 'H:MM:SS' string to a Timedelta. Blank -> NaT."""
    if not t or not isinstance(t, str) or not t.strip():
        return pd.NaT
    parts = t.strip().split(":")
    try:
        parts = [int(p) for p in parts]
    except ValueError:
        return pd.NaT
    if len(parts) == 2:
        m, s = parts
        return pd.Timedelta(minutes=m, seconds=s)
    if len(parts) == 3:
        h, m, s = parts
        return pd.Timedelta(hours=h, minutes=m, seconds=s)
    return pd.NaT


def format_timedelta(td) -> str:
    """Format a Timedelta back to 'M:SS' or 'H:MM:SS'. NaT -> '' (blank)."""
    if pd.isna(td):
        return ""
    total_s = int(td.total_seconds())
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def to_int(s):
    """Strip a trailing '.' (e.g. '1.') and parse to int; None if not numeric."""
    if not s:
        return None
    s = str(s).strip().rstrip(".")
    return int(s) if s.isdigit() else None


def format_name(display_name: str, name_format: str) -> str:
    """Normalise a name to 'First Last'. 'lastfirst' reorders 'Last, First'."""
    display_name = (display_name or "").strip()
    if name_format == "lastfirst" and "," in display_name:
        last, first = display_name.split(",", 1)
        return f"{first.strip()} {last.strip()}"
    return display_name


def _safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


def raw_path(event_id: str, listname: str) -> Path:
    return RAW_DIR / f"{event_id}__{_safe(listname)}.raw.csv"


# ──────────────────────────────────────────────────────────────────────────────
# Stage 1: scrape -> raw CSV (no interpretation)
# ──────────────────────────────────────────────────────────────────────────────
class RaceResultClient:
    """Minimal client for the RRPublish JSON API.

    Two URL layouts exist in the wild: the newer ``/{event}/{page}/...`` and the
    older ``/{event}/RRPublish/data/...``. The newer layout currently answers for
    every known event, but we probe and fall back so any URL keeps working.
    """

    def __init__(self, event_id: str, page: str = "results"):
        self.event_id = str(event_id)
        self.page = page
        self.base, self.config = self._connect()

    def _connect(self):
        candidates = [
            (f"https://my.raceresult.com/{self.event_id}/{self.page}", {"noVisitor": "1"}),
            (f"https://my.raceresult.com/{self.event_id}/RRPublish/data",
             {"page": self.page, "noVisitor": "1"}),
        ]
        last_err = None
        for base, params in candidates:
            try:
                r = requests.get(f"{base}/config", params=params, timeout=30, headers=_HEADERS)
                if r.ok:
                    return base, r.json()
                last_err = f"{r.status_code} at {base}"
            except requests.RequestException as e:  # pragma: no cover - network
                last_err = str(e)
        raise RuntimeError(f"Could not reach RaceResult config for event {self.event_id}: {last_err}")

    @property
    def key(self) -> str:
        return self.config["key"]

    def list_names(self) -> list[str]:
        """List names published on the results page (from the config 'Tab')."""
        lists = (self.config.get("Tab", {}).get("Config", {}) or {}).get("Lists", [])
        # Preserve order, drop duplicates.
        seen, names = set(), []
        for entry in lists:
            n = entry.get("Name")
            if n and n not in seen:
                seen.add(n)
                names.append(n)
        return names

    def fetch_list(self, listname: str) -> dict:
        r = requests.get(
            f"{self.base}/list",
            params={"key": self.key, "listname": listname, "page": self.page, "r": "all"},
            timeout=30,
            headers=_HEADERS,
        )
        r.raise_for_status()
        return r.json()


def _flatten_list(payload: dict):
    """Flatten the nested ``data`` of a list response into tagged rows.

    Lists nest either one level (contest -> [rows]) or two (contest ->
    age-group -> [rows]). Returns (datafields, rows) where each row is
    (contest_key, group_key, [field values]). group_key is '' when absent.
    """
    datafields = payload.get("DataFields", []) or []
    rows = []
    for k1, v1 in (payload.get("data", {}) or {}).items():
        if isinstance(v1, dict):
            for k2, group_rows in v1.items():
                for r in group_rows:
                    rows.append((k1, k2, r))
        elif isinstance(v1, list):
            for r in v1:
                rows.append((k1, "", r))
    return datafields, rows


def write_raw_csv(payload: dict, path: Path) -> Path:
    """Write a list response verbatim to a raw CSV (overwrites; never appends)."""
    datafields, rows = _flatten_list(payload)
    width = len(datafields)
    table = []
    for contest, group, values in rows:
        values = list(values) + [""] * (width - len(values))  # pad short rows
        table.append([contest, group, *values[:width]])
    # Duplicate DataField labels are allowed; processing reads by position.
    df = pd.DataFrame(table, columns=_META_COLS + list(datafields))
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    return path


def scrape_event(spec: EventSpec) -> dict:
    """Fetch the lists this event needs and dump each to a raw CSV. Idempotent."""
    client = RaceResultClient(spec.event_id)
    written = {}
    for listname in [spec.main_list, spec.ag_list]:
        if not listname:
            continue
        payload = client.fetch_list(listname)
        written[listname] = write_raw_csv(payload, spec.raw_path(listname))
    return written


def scrape_url(url: str, listnames: list[str] | None = None) -> dict:
    """General entry point: dump raw CSVs for any RaceResult results URL.

    ``url`` may be a full my.raceresult.com link or a bare event id. When
    ``listnames`` is None, every list published on the results page is dumped.
    """
    m = re.search(r"(\d{4,})", str(url))
    if not m:
        raise ValueError(f"Could not find an event id in URL: {url!r}")
    event_id = m.group(1)
    client = RaceResultClient(event_id)
    names = listnames if listnames is not None else client.list_names()
    written = {}
    for listname in names:
        payload = client.fetch_list(listname)
        written[listname] = write_raw_csv(payload, raw_path(event_id, listname))
    return written


# ──────────────────────────────────────────────────────────────────────────────
# Stage 2: process raw CSV(s) -> standard 13-column processed CSV
# ──────────────────────────────────────────────────────────────────────────────
def _load_raw(path: Path) -> list:
    """Read a raw CSV back into rows of [contest, group, *field_values] strings."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    return df.values.tolist()


def _build_age_group_map(spec: EventSpec) -> dict:
    """Return {participant_id: (age_group_band, group_rank)} from the AG raw CSV.

    The band comes from the inner age-group key (e.g. '#2_M16-19' -> 'M16-19').
    When the event carries the band inline in the main list, only the rank is
    used downstream.
    """
    if not spec.ag_list:
        return {}
    mapping = {}
    for _contest, group, *values in _load_raw(spec.raw_path(spec.ag_list)):
        band = group.split("_", 1)[1] if "_" in group else group
        pid = str(values[spec.ag_id_idx])
        mapping[pid] = (band, to_int(values[spec.ag_rank_idx]))
    return mapping


def _apply_identity_swaps(df: pd.DataFrame, swaps) -> pd.DataFrame:
    """Swap person-identity fields between mis-attributed athletes.

    Place, Bib and the split times stay on their rows; only the identity columns
    move, so each athlete is credited with their actual performance.
    """
    identity_cols = ["Name", "Age_Group", "Group_Rank", "Class", "Club"]
    for name_a, name_b in swaps:
        ia = df.index[df["Name"] == name_a]
        ib = df.index[df["Name"] == name_b]
        if len(ia) == 1 and len(ib) == 1:
            ia, ib = ia[0], ib[0]
            for col in identity_cols:
                df.at[ia, col], df.at[ib, col] = df.at[ib, col], df.at[ia, col]
    return df


def parse_event(spec: EventSpec) -> pd.DataFrame:
    """Build the standard 13-column DataFrame from this event's raw CSVs."""
    age_map = _build_age_group_map(spec)
    s = spec.split_idx
    records = []
    for contest, _group, *values in _load_raw(spec.raw_path(spec.main_list)):
        if spec.main_contest_prefix and not contest.startswith(spec.main_contest_prefix):
            continue
        pid = str(values[spec.id_idx])
        band, group_rank = age_map.get(pid, ("", None))
        age_group = values[spec.agegroup_idx] if spec.agegroup_idx is not None else band
        cls = values[spec.class_idx] or ""
        if spec.class_map:
            cls = spec.class_map.get(cls.strip().lower(), cls)
        records.append({
            "Place":      to_int(values[spec.place_idx]),
            "Bib":        to_int(values[spec.bib_idx]),
            "Name":       format_name(values[spec.name_idx], spec.name_format),
            "Age_Group":  age_group or "",
            "Group_Rank": group_rank,
            "Class":      cls,
            "Club":       values[spec.club_idx] or "",
            "Swim":       to_timedelta(values[s[0]]),
            "T1":         to_timedelta(values[s[1]]),
            "Bike":       to_timedelta(values[s[2]]),
            "T2":         to_timedelta(values[s[3]]),
            "Run":        to_timedelta(values[s[4]]),
            "Finish":     to_timedelta(values[s[5]]),
        })

    df = pd.DataFrame(records, columns=STANDARD_COLS)
    if not df.empty:
        df = df.sort_values("Place", na_position="last").reset_index(drop=True)
        df["Place"] = df["Place"].astype("Int64")
        df["Group_Rank"] = df["Group_Rank"].astype("Int64")
        df = _apply_identity_swaps(df, spec.identity_swaps)
    return df


def save_processed(df: pd.DataFrame, path: Path) -> Path:
    """Write the standard DataFrame to CSV with readable time strings (overwrites)."""
    out = df.copy()
    for col in SPLIT_COLS:
        out[col] = out[col].map(format_timedelta)
    out.to_csv(path, index=False, encoding="utf-8")
    return path


def process_event(spec: EventSpec) -> Path:
    """Read this event's raw CSV(s) and (re)write its processed CSV. Idempotent."""
    df = parse_event(spec)
    return save_processed(df, spec.processed_path)


def build_event(spec: EventSpec) -> Path:
    """Scrape then process one event end-to-end. Returns the processed CSV path."""
    scrape_event(spec)
    return process_event(spec)


def load_processed_csv(path: str) -> pd.DataFrame:
    """Load a processed CSV back into the standard 13-column format.

    This is the loader the app's REGISTRY uses: it re-parses the readable time
    strings into pd.Timedelta and restores the nullable-int dtypes so the output
    matches parse_event() / data_format.md.
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for col in ("Place", "Bib", "Group_Rank"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in SPLIT_COLS:
        df[col] = df[col].map(to_timedelta)
    return df
