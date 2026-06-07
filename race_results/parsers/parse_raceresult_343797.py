"""Parser for Fastnet Sprint Triathlon 2025 results from my.raceresult.com.

Same RaceResult "RRPublish" JSON API as the 2026 event (see
parse_raceresult_402195.py), but the 2025 event exposes different lists and a
different column layout, so it gets its own self-contained parser.

Main list "Result Lists|Full Results" already carries the age-group band inline;
the "Age Group Results - Win" list is used only for Group_Rank (rank within band).
Returns a DataFrame in the standard 13-column format described in data_format.md.
"""
from pathlib import Path
import requests
import pandas as pd

EVENT_ID = "343797"
BASE = f"https://my.raceresult.com/{EVENT_ID}/RRPublish/data"

MAIN_LIST = "Result Lists|Full Results"
AG_LIST = "Result Lists|Age Group Results - Win"

# "Full Results" returns all three contests (#1_Sprint, #2_Sprint Relay,
# #3_Try a Tri) in one payload. We keep only the individual Sprint contest
# (group keys prefixed "#1_") so Place is a single clean ranking, matching the
# 2026 parser's scope.
SPRINT_PREFIX = "#1_"

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "Fastnet_Sprint_Triathlon_2025.csv"

SPLIT_COLS = ["Swim", "T1", "Bike", "T2", "Run", "Finish"]

# Column index within each "Full Results" data row.
# DataFields: BIB, ID, WithStatus([TotalRankp]), FLNAME, SEX,
#             AGEGROUP1.NAMESHORT, ATF2(Club), Swim, Transition1, Cycle,
#             Transition2, Run, TIME
F_BIB, F_ID, F_PLACE, F_NAME, F_SEX, F_AGEGROUP, F_CLUB = 0, 1, 2, 3, 4, 5, 6
F_SWIM, F_T1, F_BIKE, F_T2, F_RUN, F_FINISH = 7, 8, 9, 10, 11, 12

# Column index within each "Age Group Results" data row.
# DataFields: BIB, ID, WithStatus([AgeGroupRankExcp]), FIRSTNAME, LASTNAME,
#             YEAR, SEX, ATF2, TIMETEXT
AG_ID, AG_RANK = 1, 2

# Map the source SEX code to the Class convention used in data_format.md.
_SEX_TO_CLASS = {"m": "Open", "f": "Female"}

# Known source data-entry errors (athlete pairs whose identities were attached to
# each other's timing rows). Same mechanism as the 2026 parser; empty for now.
_IDENTITY_COLS = ["Name", "Age_Group", "Group_Rank", "Class", "Club"]
_IDENTITY_SWAPS = []


def _to_timedelta(t) -> pd.Timedelta:
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


def _format_timedelta(td) -> str:
    """Format a Timedelta back to 'M:SS' or 'H:MM:SS'. NaT -> '' (blank)."""
    if pd.isna(td):
        return ""
    total_s = int(td.total_seconds())
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _to_int(s):
    """Strip a trailing '.' (e.g. '1.') and parse to int; None if not numeric."""
    if not s:
        return None
    s = str(s).strip().rstrip(".")
    return int(s) if s.isdigit() else None


def _fetch_config() -> dict:
    r = requests.get(f"{BASE}/config", params={"page": "results", "noVisitor": "1"}, timeout=30)
    r.raise_for_status()
    return r.json()


def _fetch_list(key: str, listname: str) -> dict:
    r = requests.get(
        f"{BASE}/list",
        params={"key": key, "listname": listname, "page": "results", "r": "all"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def _build_age_group_map(key: str) -> dict:
    """Return {participant_id: group_rank} from the nested age-group list.

    Data is nested: data -> '#1_Sprint' -> '#2_F16-19' -> [rows]. The band is
    already inline in the main list, so here we only need the rank (column 2).
    """
    payload = _fetch_list(key, AG_LIST)
    mapping = {}
    for _contest, age_groups in payload.get("data", {}).items():
        if not isinstance(age_groups, dict):
            continue
        for _group_key, rows in age_groups.items():
            for row in rows:
                mapping[str(row[AG_ID])] = _to_int(row[AG_RANK])
    return mapping


def _apply_identity_swaps(df: pd.DataFrame) -> pd.DataFrame:
    """Swap person-identity fields between mis-attributed athletes (see _IDENTITY_SWAPS)."""
    for name_a, name_b in _IDENTITY_SWAPS:
        ia = df.index[df["Name"] == name_a]
        ib = df.index[df["Name"] == name_b]
        if len(ia) == 1 and len(ib) == 1:
            ia, ib = ia[0], ib[0]
            for col in _IDENTITY_COLS:
                df.at[ia, col], df.at[ib, col] = df.at[ib, col], df.at[ia, col]
    return df


def load_results(url: str = None) -> pd.DataFrame:
    """Fetch and parse the race results into the standard 13-column DataFrame."""
    config = _fetch_config()
    key = config["key"]

    rank_map = _build_age_group_map(key)

    payload = _fetch_list(key, MAIN_LIST)
    records = []
    for group_key, rows in payload.get("data", {}).items():
        if not group_key.startswith(SPRINT_PREFIX):
            continue
        for row in rows:
            pid = str(row[F_ID])
            sex = (row[F_SEX] or "").strip().lower()
            records.append({
                "Place":      _to_int(row[F_PLACE]),
                "Bib":        _to_int(row[F_BIB]),
                "Name":       row[F_NAME].strip(),
                "Age_Group":  row[F_AGEGROUP] or "",
                "Group_Rank": rank_map.get(pid),
                "Class":      _SEX_TO_CLASS.get(sex, row[F_SEX] or ""),
                "Club":       row[F_CLUB] or "",
                "Swim":       _to_timedelta(row[F_SWIM]),
                "T1":         _to_timedelta(row[F_T1]),
                "Bike":       _to_timedelta(row[F_BIKE]),
                "T2":         _to_timedelta(row[F_T2]),
                "Run":        _to_timedelta(row[F_RUN]),
                "Finish":     _to_timedelta(row[F_FINISH]),
            })

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.sort_values("Place", na_position="last").reset_index(drop=True)
        df["Place"] = df["Place"].astype("Int64")
        df["Group_Rank"] = df["Group_Rank"].astype("Int64")
        df = _apply_identity_swaps(df)
    return df


def save_results(df: pd.DataFrame, path: Path = OUTPUT_PATH) -> Path:
    """Write the parsed results to CSV, formatting split times as readable strings."""
    out = df.copy()
    for col in SPLIT_COLS:
        out[col] = out[col].map(_format_timedelta)
    out.to_csv(path, index=False, encoding="utf-8")
    return path


def load_results_csv(path: str = OUTPUT_PATH) -> pd.DataFrame:
    """Load a previously-saved results CSV back into the standard 13-column format."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for col in ("Place", "Bib", "Group_Rank"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in SPLIT_COLS:
        df[col] = df[col].map(_to_timedelta)
    df = _apply_identity_swaps(df)
    return df


if __name__ == "__main__":
    df = load_results()
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)
    print(df.head(12))
    print(f"\nTotal records: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")
    print(f"\nClass counts:\n{df['Class'].value_counts()}")
    print(f"\nAge_Group counts (top 10):\n{df['Age_Group'].value_counts().head(10)}")
    print(f"\nRows missing Age_Group: {(df['Age_Group'] == '').sum()}")
    print(f"Rows missing any split: {df[SPLIT_COLS].isna().any(axis=1).sum()}")

    out_path = save_results(df)
    print(f"\nSaved {len(df)} rows to {out_path}")
