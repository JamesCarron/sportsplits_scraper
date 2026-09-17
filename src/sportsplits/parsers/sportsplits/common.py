"""Parser for Sportsplits (sportsplits.com) race results.

Sportsplits pages are server-rendered HTML with no JSON API. robots.txt disallows
AI crawlers and a direct server-side fetch returns HTTP 403 (Cloudflare), so this
cannot be scraped with plain `requests` -- results are scraped via a browser
(Claude in Chrome, the user's own authenticated session), which loads normally
and only occasionally hits a Cloudflare Turnstile interstitial that resolves
itself within a few seconds.

Raw format: data/raw/sportsplits/<race-slug>.json, one file per race, holding
every "event" (distance/category within that race, e.g. Sprint/Olympic) as
{headers: [...], rows: [[...], ...]} -- the literal scraped table, one row per
athlete, already sorted by finishing position. Saved by hand through the
browser (see the scraping script used for triathy-2025-2025.json as a
reference); this module only maps that JSON to the standard 13-column format.

Column headers vary a little between races/events (e.g. "Cycle" vs "Bike",
"Category (Pos)" vs "Category", "Gun Time" vs "Finish Time", "Prologue" for a
duathlon's run-before-bike leg instead of "Swim") -- _row_to_record() maps by
header name with fallbacks rather than assuming a fixed column order.
"""
import json
import re

import pandas as pd

from sportsplits.config import RAW_DIR
from sportsplits.parsers.raceresult.common import to_timedelta, STANDARD_COLS

_RAW_DIR = RAW_DIR / "sportsplits"

_CLASS_MAP = {"Male": "Open", "Female": "Female", "Mixed": "RELAY"}

_NAME_RE = re.compile(r"^(.*)\s+\(#(\S+)\)\s*$")
_PAREN_RANK_RE = re.compile(r"^(.*?)\s*\((\d+)\)\s*$")


def _split_name_bib(text: str):
    """'Ronan POTTERTON (#1266)' -> ('Ronan POTTERTON', '1266')."""
    m = _NAME_RE.match((text or "").strip())
    if m:
        return m.group(1).strip(), m.group(2)
    return (text or "").strip(), None


def _split_paren_rank(text: str):
    """'25-29 (1)' -> ('25-29', 1). '25-29' (no rank) -> ('25-29', None)."""
    text = (text or "").strip()
    if not text:
        return "", None
    m = _PAREN_RANK_RE.match(text)
    if m:
        return m.group(1).strip(), int(m.group(2))
    return text, None


def _to_int(v):
    v = (v or "").strip()
    return int(v) if v.isdigit() else None


def _clean_club(text: str) -> str:
    """'GBR\\n\\t\\t...\\t|' -> 'GBR'. The 'Representing' column pads its value with
    a run of whitespace/newlines then a trailing '|' (a flag-icon separator that
    doesn't survive text extraction) -- collapse whitespace and drop it."""
    text = re.sub(r"\s+", " ", (text or "")).strip()
    return re.sub(r"\s*\|\s*$", "", text).strip()


def _row_to_record(headers: list, row: list) -> dict:
    d = dict(zip(headers, row))
    name, bib = _split_name_bib(d.get("Name", ""))
    age_group, group_rank = _split_paren_rank(d.get("Category (Pos)") or d.get("Category", ""))
    gender, _ = _split_paren_rank(d.get("Gender (Pos)") or d.get("Gender", ""))

    return {
        "Place": _to_int(d.get("Pos")),
        "Bib": _to_int(bib),
        "Name": name,
        "Age_Group": age_group,
        "Group_Rank": group_rank,
        "Class": _CLASS_MAP.get(gender, gender or ""),
        "Club": _clean_club(d.get("Representing") or d.get("Club") or ""),
        "Swim": to_timedelta(d.get("Swim") or d.get("Prologue")),
        "T1": to_timedelta(d.get("T1")),
        "Bike": to_timedelta(d.get("Cycle") or d.get("Bike")),
        "T2": to_timedelta(d.get("T2")),
        "Run": to_timedelta(d.get("Run")),
        "Finish": to_timedelta(d.get("Finish Time") or d.get("Gun Time")),
    }


def parse_event(headers: list, rows: list) -> pd.DataFrame:
    """headers/rows: as scraped -- one row per athlete, pre-sorted by position."""
    records = [_row_to_record(headers, row) for row in rows]
    df = pd.DataFrame(records, columns=STANDARD_COLS)
    if not df.empty:
        df = df.sort_values("Place", na_position="last").reset_index(drop=True)
        df["Place"] = df["Place"].astype("Int64")
        df["Group_Rank"] = df["Group_Rank"].astype("Int64")
    return df


def load_race(slug: str) -> dict:
    """Returns {event_number: (event_name, standard-format DataFrame)}."""
    raw = json.loads((_RAW_DIR / f"{slug}.json").read_text(encoding="utf-8"))
    return {num: (ev["name"], parse_event(ev["headers"], ev["rows"])) for num, ev in raw["events"].items()}
